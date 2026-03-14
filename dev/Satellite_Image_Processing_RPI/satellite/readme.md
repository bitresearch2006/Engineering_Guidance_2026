Satellite Function on OpenFaaS (faasd)
This repo contains an OpenFaaS function satellite deployed on a single‑node faasd setup (systemd + containerd). We build the image with faas-cli, push to a local Docker registry at localhost:5000, import the same tag into containerd (faasd’s runtime), then deploy via the OpenFaaS gateway.

Why this workflow?
faasd uses containerd (not Docker). By importing the image into containerd under the same reference used in the YAML (localhost:5000/satellite:latest), the function can start without pulling from the registry—even after reboots. (The registry is still useful for versioning and local sharing.)


1) Quick Start
Prerequisites

faasd (gateway, provider, nats, queue‑worker, prometheus) running via systemd
Docker daemon running (for local builds and local registry)
Local Docker registry container on port 5000
faas-cli and curl installed


Your satellite.yml is already configured to use the local registry:
YAMLimage: localhost:5000/satellite:latestShow more lines
 [build | Txt]


2) Build → Import → Deploy (standard flow)

We keep the image tag localhost:5000/satellite:latest in both the build and YAML so all components agree on the same reference. The Gradle tasks below are defined in your project. [build | Txt]

A) Build & push to local registry
Shell./gradlew DockerPushShow more lines
This executes:

faas-cli build -f build/satellite.yml (inside build/)
faas-cli push -f build/satellite.yml → pushes localhost:5000/satellite:latest to the local registry [build | Txt]

B) Import the same image into containerd (faasd)

Run as root (only this step): we stream the Docker image directly into containerd’s openfaas namespace.

Shellsudo -E ./gradlew --no-daemon faasPushToContainerdShow more lines
This task verifies the image exists locally and runs:
Shelldocker save localhost:5000/satellite:latest | /usr/local/bin/ctr -n openfaas images import -``Show more lines
so the image is available to faasd without any pull. [build | Txt]
C) Deploy via the gateway
Shell./gradlew faasDeployShow more lines
This runs faas-cli deploy -f build/satellite.yml and reports the function URL (e.g., http://127.0.0.1:8080/function/satellite). [build | Txt]

3) Invoke the function
The handler expects JSON. Use POST:
Shellcurl -i -X POST \  -H "Content-Type: application/json" \  -d '{"arg":"img"}' \  http://127.0.0.1:8080/function/satelliteShow more lines
If you send a GET or a POST without JSON, the function may return 4xx/5xx because it tries to parse event.body as JSON.

4) Post‑reboot health checks
After a restart, you should not need any pull because the image is already in containerd.
Shell# A) Image in containerd under the exact reference from YAMLsudo ctr -n openfaas images ls | grep 'localhost:5000/satellite:latest'# B) Function status via gatewayfaas-cli listfaas-cli describe satellite# C) Function runtime (functions live in "openfaas-fn")sudo ctr -n openfaas-fn containers ls | grep satellite || echo "no fn containers"sudo ctr -n openfaas-fn tasks ls | grep satellite || echo "no running fn tasks"Show more lines

System services (gateway, queue‑worker, prometheus, nats) appear in the openfaas namespace; functions appear in openfaas-fn. Use the correct namespace when inspecting runtime.
(Your earlier checks showed core services in openfaas, function containers/tasks in openfaas-fn.)

To force a cold start (if scaled to 0):
Shellcurl -i -X POST -H "Content-Type: application/json" \  -d '{"arg":"img"}' \  http://127.0.0.1:8080/function/satelliteShow more lines

5) Diagnostics & Troubleshooting
Common commands
Shell# Gateway up?curl -s http://127.0.0.1:8080/system/functions | jq . || curl -s http://127.0.0.1:8080/system/functions# Function statusfaas-cli listfaas-cli describe satellitefaas-cli logs satellite# Function runtime (containerd)sudo ctr -n openfaas-fn containers ls | grep satellite || truesudo ctr -n openfaas-fn tasks ls | grep satellite || true# Image present locally in containerd?sudo ctr -n openfaas images ls | grep 'localhost:5000/satellite:latest'# Registry has the image?curl -s http://localhost:5000/v2/_catalogdocker pull localhost:5000/satellite:latestShow more lines
If Replicas: 0 after reboot

Confirm the image exists locally in containerd under the same reference as your YAML (localhost:5000/satellite:latest).
If using autoscaling, you may be in scale‑to‑zero. Add scaling labels (below) to keep 1 warm replica.
If containerd still tries to pull, ensure containerd registry mirrors/hosts are configured for localhost:5000 (HTTP). Alternatively, stick with the import step which avoids any pull.


6) Scaling settings
Add these labels to keep a warm replica and bound autoscaling:
YAMLlabels:  com.openfaas.scale.min: "1"  com.openfaas.scale.max: "4"  # Optional guard to prevent idling:  # com.openfaas.scale.zero: "false"Show more lines

These labels are read by the OpenFaaS scaler; you already keep min_replicas: 1 in the function spec, but labels make the intent explicit and compatible across providers. Update satellite.yml and redeploy to apply them. [build | Txt]


7) Files explained
build.gradle (Gradle build)
Your Gradle file defines a straightforward pipeline:

downloadTemplate / copySources – retrieves the template (python3-http-debian) and copies the handler + YAML into build/.
DockerBuild – runs faas-cli build -f build/satellite.yml.
DockerPush – runs faas-cli push -f build/satellite.yml (pushes localhost:5000/satellite:latest).
faasPushToContainerd – (run with sudo) streams the local Docker image into containerd:
docker save ${imageName} | /usr/local/bin/ctr -n openfaas images import -
faasDeploy – runs faas-cli deploy -f build/satellite.yml.

Key variables:
Groovyext {  functionName = "satellite"  imageName    = "localhost:5000/${functionName}:latest"  gatewayUrl   = "http://127.0.0.1:8080"  templateName = "python3-http-debian"  templateRepo = "https://github.com/bitresearch2006/faas_templates.git"  templateBranch = "main"}Show more lines

The tasks and imageName shown above are defined in your currently uploaded build.txt.
Make sure faasDeploy depends on copySources (so the freshest YAML is used) or re‑run copySources before deploy. [build | Txt]

satellite.yml (function spec)
Important fields (as in your current file):
YAMLprovider:  name: openfaas  gateway: http://127.0.0.1:8080functions:  satellite:    lang: python3-http-debian    handler: ./main    image: localhost:5000/satellite:latest    min_replicas: 1    build_args:      ADDITIONAL_PACKAGE: ""    environment:      DIAGNOSTICS: "true"      LOG_DIR: "/tmp/satellite_logs"    # Optional scaling labels:    # labels:    #   com.openfaas.scale.min: "1"    #   com.openfaas.scale.max: "4"Show more lines

This definition matches your repo’s function config; only the labels: block is optional if you decide to keep one warm replica. [build | Txt]


8) Admin (UI login)
OpenFaaS UI is at http://127.0.0.1:8080/ui and uses basic auth:
Shell# usernamesudo cat /var/lib/faasd/secrets/basic-auth-user# passwordsudo cat /var/lib/faasd/secrets/basic-auth-passwordShow more lines
Log in with admin / the password printed above.

9) Typical one‑liners
Build & push:
Shell./gradlew DockerPushShow more lines
Import into containerd (run as root):
Shellsudo -E ./gradlew --no-daemon faasPushToContainerdShow more lines
Deploy:
Shell./gradlew faasDeployShow more lines
Invoke with JSON:
Shellcurl -i -X POST -H "Content-Type: application/json" \  -d '{"arg":"img"}' \  http://127.0.0.1:8080/function/satelliteShow more lines
Keep one warm replica (add to YAML):
YAMLlabels:  com.openfaas.scale.min: "1"  com.openfaas.scale.max: "4"Show more lines

10) Notes

If you change code or Python requirements → rebuild & push, re‑import, then deploy.
If you change only YAML labels/env → deploy is enough.
Images in containerd persist across reboots; after you import once, faasd can restart the function without contacting the registry (as long as the image reference matches the YAML).


Appendix: Why two runtimes (Docker & containerd)?

Docker is used for building and pushing images to the local registry.
faasd runs on containerd (via systemd). Functions are containers spawned by containerd, not Docker. That’s why we import the image into containerd or configure containerd to pull from your registry.

