# Satellite Function on OpenFaaS (faasd)

This repo contains an OpenFaaS function **`satellite`** deployed on a single‑node **faasd** setup (systemd + containerd). We **build** the image with `faas-cli`, **push** to a local Docker registry at `localhost:5000`, **import** the same tag into **containerd** (faasd’s runtime), then **deploy** via the OpenFaaS gateway.

> **Why this workflow?**  
> faasd uses **containerd** (not Docker). By importing the image into containerd under the **same reference** used in the YAML (`localhost:5000/satellite:latest`), the function can start **without pulling** from the registry—even after reboots. The local registry is still useful for versioning and sharing across your machines.

---

## 1) Quick Start

### Prerequisites

- faasd services running via systemd: gateway, provider, nats, queue‑worker, prometheus  
- Docker daemon running (for local builds and the local registry)  
- Local Docker registry container on port **5000**  
- `faas-cli` and `curl` installed

Your `satellite.yml` is already configured to use the local registry:

```yaml
functions:
  satellite:
    image: localhost:5000/satellite:latest
```

---

## 2) Build → Import → Deploy (standard flow)

We keep the image tag **`localhost:5000/satellite:latest`** in both the build and YAML so all components agree on the same reference. The Gradle tasks below are defined in this project.

### A) Build & push to local registry

```bash
./gradlew DockerPush
```

This executes:

- `faas-cli build -f build/satellite.yml` (inside `build/`)
- `faas-cli push -f build/satellite.yml` → pushes `localhost:5000/satellite:latest` to the local registry

### B) Import the same image into containerd (faasd)

> **Run as root** (only this step). We stream the Docker image into containerd’s `openfaas` namespace, so faasd can start without pulling.

```bash
sudo -E ./gradlew --no-daemon faasPushToContainerd
```

Under the hood this runs:

```bash
docker save localhost:5000/satellite:latest | /usr/local/bin/ctr -n openfaas images import -
```

### C) Deploy via the gateway

```bash
./gradlew faasDeploy
```

This runs `faas-cli deploy -f build/satellite.yml` and prints the function URL, e.g.:

```
http://127.0.0.1:8080/function/satellite
```

---

## 3) Invoke the function

The handler expects **JSON**. Use **POST**:

```bash
curl -i -X POST \
  -H "Content-Type: application/json" \
  -d '{"arg":"img"}' \
  http://127.0.0.1:8080/function/satellite
```

> If you send a GET or a POST without JSON, the function may return 4xx/5xx because it parses `event.body` as JSON.

---

## 4) Post‑reboot health checks

After a restart, you shouldn’t need any pull because the image is already in containerd.

```bash
# A) Image in containerd under the exact reference from YAML
sudo ctr -n openfaas images ls | grep 'localhost:5000/satellite:latest'

# B) Function status via gateway
faas-cli list
faas-cli describe satellite

# C) Function runtime (functions live in "openfaas-fn")
sudo ctr -n openfaas-fn containers ls | grep satellite || echo "no fn containers"
sudo ctr -n openfaas-fn tasks ls | grep satellite || echo "no running fn tasks"
```

> System services (gateway, queue‑worker, prometheus, nats) appear in the **`openfaas`** namespace; functions appear in **`openfaas-fn`**.

To force a cold start (if scaled to 0):

```bash
curl -i -X POST -H "Content-Type: application/json" \
  -d '{"arg":"img"}' \
  http://127.0.0.1:8080/function/satellite
```

---

## 5) Diagnostics & Troubleshooting

### Common commands

```bash
# Gateway up?
curl -s http://127.0.0.1:8080/system/functions | jq . || curl -s http://127.0.0.1:8080/system/functions

# Function status
faas-cli list
faas-cli describe satellite
faas-cli logs satellite

# Function runtime (containerd)
sudo ctr -n openfaas-fn containers ls | grep satellite || true
sudo ctr -n openfaas-fn tasks ls | grep satellite || true

# Image present locally in containerd?
sudo ctr -n openfaas images ls | grep 'localhost:5000/satellite:latest'

# Registry has the image?
curl -s http://localhost:5000/v2/_catalog
docker pull localhost:5000/satellite:latest
```

### If `Replicas: 0` after reboot

- Confirm the image exists in containerd under the **same reference** as your YAML (`localhost:5000/satellite:latest`).  
- If using autoscaling, you may be in **scale‑to‑zero**. Add scaling labels (below) to keep 1 warm replica.  
- If containerd still tries to pull, configure containerd registry mirrors/hosts for `localhost:5000` (HTTP). Alternatively, stick with the **import step**, which avoids any pull.

---

## 6) Scaling settings (Not worked use cold start after reboot under heading 10)

Add these labels to keep a warm replica and bound autoscaling:

```yaml
labels:
  com.openfaas.scale.min: "1"
  com.openfaas.scale.max: "4"
  # Optional guard to prevent idling entirely:
  # com.openfaas.scale.zero: "false"
```

> These labels are read by the OpenFaaS scaler. You also have `min_replicas: 1` in the spec, but labels make the intent explicit and compatible across providers. Update `satellite.yml` and redeploy to apply them.

---

## 7) Files explained

### `build.gradle` (Gradle build)

A straightforward pipeline:

- **`downloadTemplate` / `copySources`** – retrieves the template (`python3-http-debian`) and copies the handler + YAML into `build/`.
- **`DockerBuild`** – `faas-cli build -f build/satellite.yml`
- **`DockerPush`** – `faas-cli push -f build/satellite.yml` → pushes `localhost:5000/satellite:latest`
- **`faasPushToContainerd`** – **(run with sudo)** streams the local Docker image into containerd:
  ```bash
  docker save ${imageName} | /usr/local/bin/ctr -n openfaas images import -
  ```
- **`faasDeploy`** – `faas-cli deploy -f build/satellite.yml`

Key variables:

```groovy
ext {
  functionName = "satellite"
  imageName    = "localhost:5000/${functionName}:latest"
  gatewayUrl   = "http://127.0.0.1:8080"
  templateName = "python3-http-debian"
  templateRepo = "https://github.com/bitresearch2006/faas_templates.git"
  templateBranch = "main"
}
```

> Ensure `faasDeploy` runs with the **fresh** YAML (either run `copySources` beforehand or make `faasDeploy` depend on it).

### `satellite.yml` (function spec)

```yaml
provider:
  name: openfaas
  gateway: http://127.0.0.1:8080

functions:
  satellite:
    lang: python3-http-debian
    handler: ./main
    image: localhost:5000/satellite:latest
    min_replicas: 1
    # Optional scaling labels:
    # labels:
    #   com.openfaas.scale.min: "1"
    #   com.openfaas.scale.max: "4"
    build_args:
      ADDITIONAL_PACKAGE: ""
    environment:
      DIAGNOSTICS: "true"
      LOG_DIR: "/tmp/satellite_logs"
```

---

## 8) Admin (UI login)

OpenFaaS UI: `http://127.0.0.1:8080/ui` (Basic Auth)

```bash
# username
sudo cat /var/lib/faasd/secrets/basic-auth-user
# password
sudo cat /var/lib/faasd/secrets/basic-auth-password
```

Log in with `admin` and the password printed above.

---

## 9) Typical one‑liners

**Build & push:**
```bash
./gradlew DockerPush
```

**Import into containerd (run as root):**
```bash
sudo -E ./gradlew --no-daemon faasPushToContainerd
```

**Deploy:**
```bash
./gradlew faasDeploy
```

**Invoke with JSON:**
```bash
curl -i -X POST -H "Content-Type: application/json" \
  -d '{"arg":"img"}' \
  http://127.0.0.1:8080/function/satellite
```

**cold start after reboot:**
```bash
enable crone:
./gradlew installWarmupCron
disable crone:
./gradlew removeWarmupCron
```

---

## 10) Notes

- If you **change code** or Python dependencies → **rebuild & push**, **re‑import**, then **deploy**.  
- If you **change only YAML** labels/env → **deploy** is enough.  
- Images in containerd **persist across reboots**; once imported, faasd can restart the function without contacting the registry (as long as the image reference matches the YAML).

---

### Appendix: Why two runtimes (Docker & containerd)?

- Docker is used for **building** images and pushing to the local registry.  
- faasd runs on **containerd** (via systemd). Functions are spawned by containerd, not Docker. That’s why we **import** the image into containerd or configure containerd to pull from your registry.
