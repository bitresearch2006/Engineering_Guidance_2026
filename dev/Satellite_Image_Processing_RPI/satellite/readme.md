# Satellite Function on OpenFaaS (faasd)

This repository contains the **satellite** OpenFaaS function deployed on a single‑node **faasd** system (systemd + containerd).  
A single Gradle command, **`faasDeploy`**, performs the entire build → push/import → deploy workflow and can also install a warm‑up cron to avoid cold starts after a reboot.

---

# 1) Before You Begin

Start the local Docker registry (required for image tagging & pushing):

```
docker run -d -p 5000:5000 --name registry registry:2
```

Verify the registry is responding:

```
curl http://localhost:5000/v2/
```

Expected output:

```
{}
```

---

# 2) One‑Command Deployment

Deploy everything in a single step:

```
./gradlew faasDeploy
```

The task performs:

1. **Build** the function (`faas-cli build`)
2. **Ensure the local registry is running**
3. **Push** the image to the registry
4. **Import** the image into containerd (`faasd` runtime)
5. **Deploy** the function via the gateway
6. **Optional:** Install boot‑time warm‑up cron

Your `satellite.yml` already points to the registry:

```yaml
image: localhost:5000/satellite:latest
```

---

# 3) Invoking the Function

Use POST with JSON:

```
curl -i -X POST   -H "Content-Type: application/json"   -d '{"arg":"img"}'   http://127.0.0.1:8080/function/satellite
```

---

# 4) Prevent Cold‑Starts After Reboot

Enable warm‑up cron:

```
./gradlew installWarmupCron
```

Disable warm‑up cron:

```
./gradlew removeWarmupCron
```

The warm‑up cron job:

- waits for OpenFaaS gateway  
- invokes the `satellite` function once  
- ensures a warm replica is ready after boot  

---

# 5) Checking System Health After Reboot

### Gateway status
```
faas-cli list
faas-cli describe satellite
```

### Image present in containerd
```
sudo ctr -n openfaas images ls | grep satellite
```

### Running function container
```
sudo ctr -n openfaas-fn containers ls | grep satellite
```

---

# 6) Rebuilding After Code Changes

```
./gradlew faasDeploy
```

This rebuilds, pushes/imports, and redeploys.

---

# 7) OpenFaaS UI Access

```
http://127.0.0.1:8080/ui
```

Credentials:

```
sudo cat /var/lib/faasd/secrets/basic-auth-user
sudo cat /var/lib/faasd/secrets/basic-auth-password
```

---

# 8) JSON Handler Expectations

The handler expects valid JSON input.  
Non‑JSON input or GET requests may trigger errors.

---

### Invoke
```
curl -i -X POST -H "Content-Type: application/json"   -d '{"arg":"img"}'   http://127.0.0.1:8080/function/satellite
```

---

# 9) Notes

- If you change code or Python dependencies → run `faasDeploy`.
- If you change only YAML settings → run `faasDeploy` or manually `faas-cli deploy`.
- containerd retains images across reboots; no re‑pull is needed.
- Docker is used only for building and local registry.

---

# Appendix: Why This Workflow?

- **Docker** builds and pushes the image.
- **containerd (faasd)** actually runs the function.
- Importing the image into containerd ensures faasd never needs to pull from the registry at runtime.
