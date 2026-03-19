# Runbook: OpenHands (Mini Phase A)

## Current local reality
- Installed CLI on the Mini: `openhands` `1.13.0`
- `openhands serve` still hardcodes the GUI launcher to `localhost:3000`
- Installed CLI persistence override variable: `OPENHANDS_PERSISTENCE_DIR`
- Locally validated in this repo: Docker-direct app smoke on `127.0.0.1:4031`
- Current optional remote operator path: `https://hands.tailfd1400.ts.net/` via `svc:hands`
- Current LiteLLM Phase B app-container-reachable gateway path:
  `http://192.168.1.71:4000/v1`
- Current bridge-mode app container does not reach LiteLLM at
  `http://host.docker.internal:4000/v1`
- Still pending: first provider-backed `plan -> patch -> validate -> summarize`
  loop inside the sandbox

## Preflight
```bash
python3.12 --version
uv --version
docker --version
df -h / /var/lib/docker
docker system df
ss -ltnp | rg ':3000|:4000|:4031|:4096' || true
```

## Install CLI
```bash
uv tool install openhands --python 3.12
```

## Prepare disposable paths
```bash
mkdir -p /home/christopherbailey/openhands-experimental/phase-a-workspace
mkdir -p /home/christopherbailey/.local/share/openhands-phasea
```

## Primary launch path (Docker-direct)
```bash
docker run -it --rm --pull=always \
  -e AGENT_SERVER_IMAGE_REPOSITORY=ghcr.io/openhands/agent-server \
  -e AGENT_SERVER_IMAGE_TAG=1.12.0-python \
  -e LOG_ALL_EVENTS=true \
  -e SANDBOX_VOLUMES=/home/christopherbailey/openhands-experimental/phase-a-workspace:/workspace:rw \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/christopherbailey/.local/share/openhands-phasea:/.openhands \
  -p 127.0.0.1:4031:3000 \
  --add-host host.docker.internal:host-gateway \
  --name openhands-app \
  docker.openhands.dev/openhands/openhands:1.5
```

For the validated local smoke on this Mini, the same contract worked with
detached mode and `--pull=never` against the already-cached app image:
```bash
docker run -d --rm \
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.openhands.dev/openhands/runtime:latest-nikolaik \
  -e LOG_ALL_EVENTS=true \
  -e SANDBOX_VOLUMES=/home/christopherbailey/openhands-experimental/phase-a-workspace:/workspace:rw \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/christopherbailey/.local/share/openhands-phasea:/.openhands \
  -p 127.0.0.1:4031:3000 \
  --add-host host.docker.internal:host-gateway \
  --name openhands-app \
  --pull=never \
  docker.openhands.dev/openhands/openhands:1.5
```

## Fallback persistence path
If the custom host persistence mount does not behave as expected, rerun once
with the documented default host path:
```bash
-v /home/christopherbailey/.openhands:/.openhands
```

## Validation
```bash
ss -ltnp | rg ':4031'
curl -fsS http://127.0.0.1:4031 >/dev/null
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | rg 'openhands-app'
docker inspect openhands-app --format '{{json .HostConfig.Binds}}'
```

## LiteLLM Phase B gate
Validate the current app-container network path first:
```bash
docker exec openhands-app python -c "import urllib.request; urllib.request.urlopen('http://192.168.1.71:4000/v1/models', timeout=10)"
docker exec openhands-app python -c "import urllib.request; urllib.request.urlopen('http://host.docker.internal:4000/health/readiness', timeout=10)"
```

Expected:
- `http://192.168.1.71:4000/v1/models` is reachable from the app container.
- `http://host.docker.internal:4000/health/readiness` is not the current live path for the bridge-mode app container.

Verify the governed worker contract through LiteLLM only:
```bash
export OPENHANDS_WORKER_KEY='<worker-key>'
export OPENHANDS_LITELLM_BASE_URL='http://192.168.1.71:4000/v1'

curl -fsS "$OPENHANDS_LITELLM_BASE_URL/models" \
  -H "Authorization: Bearer $OPENHANDS_WORKER_KEY" | jq .

curl -fsS "$OPENHANDS_LITELLM_BASE_URL/model/info" \
  -H "Authorization: Bearer $OPENHANDS_WORKER_KEY" | jq .

```

Expected:
- Phase B LiteLLM handoff is currently deferred.
- Do not expect an OpenHands-specific model alias in the active gateway contract.
- Re-open this runbook only after a new backend-hardening plan defines the
  future OpenHands model/worker contract.

## Optional tailnet-only access
Enable a dedicated Tailscale Service for OpenHands:
```bash
tailscale serve --bg --service=svc:hands 4031
```

If the CLI rejects the bare port target, use:
```bash
tailscale serve --bg --service=svc:hands http://127.0.0.1:4031
```

Validate the tailnet service mapping:
```bash
tailscale serve status --json | jq '.Services["svc:hands"]'
tailscale serve status
```

Expected remote operator URL:
```text
https://hands.tailfd1400.ts.net/
```

OpenCode boundary:
- OpenCode Web now uses dedicated Tailscale Service `svc:codeagent`
- OpenHands tasks must not modify that mapping while working on `svc:hands`

## First trust-building loop
Prepared scratch repo:
`/home/christopherbailey/openhands-experimental/phase-a-workspace/scratch-repo`

Current failing check:
```bash
cd /home/christopherbailey/openhands-experimental/phase-a-workspace/scratch-repo
python3 -m unittest
```

Use that scratch repo, then prompt OpenHands to:

1. explain the plan
2. patch the file
3. run `python -m unittest`
4. summarize the change

## Teardown
```bash
docker stop openhands-app
tailscale serve clear svc:hands
rm -rf /home/christopherbailey/openhands-experimental/phase-a-workspace
rm -rf /home/christopherbailey/.local/share/openhands-phasea
# if fallback was used:
rm -rf /home/christopherbailey/.openhands
```
