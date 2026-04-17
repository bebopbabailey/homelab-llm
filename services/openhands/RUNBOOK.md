# Runbook: OpenHands (Mini Phase A)

## Current runtime contract
- Repo-managed runtime unit: `platform/ops/systemd/openhands.service`
- Installed host unit: `/etc/systemd/system/openhands.service`
- Installed host env file: `/etc/openhands/env`
- Local UI: `http://127.0.0.1:4031`
- Tailnet operator URL: `https://hands.tailfd1400.ts.net/` via `svc:hands`
- Runtime owner: `systemd` launches Docker container `openhands-app`
- `openhands serve` remains secondary/operator-only because it centers on `localhost:3000`
- Current LiteLLM Phase B worker alias is reserved/internal:
  `litellm_proxy/code-reasoning`
- Canonical LiteLLM container path for Phase B:
  `http://host.docker.internal:4000/v1`
- Verified fallback/reference path:
  `http://192.168.1.71:4000/v1`
- Experimental shadow contract for Qwen-Agent:
  - preferred direct provider path:
    - model: `qwen-agent-coder-next-shadow`
    - token file: `/etc/homelab-llm/qwen-agent-proxy.secret.env`
    - base URL: `http://host.docker.internal:4021/v1`
  - optional LiteLLM validation path:
    - model: `litellm_proxy/code-qwen-agent`
    - key file: `/home/christopherbailey/.config/openhands/worker_api_key_shadow`
    - shadow LiteLLM base URL: `http://host.docker.internal:4001/v1`
- Still pending: first provider-backed `plan -> patch -> validate -> summarize`
  loop inside the sandbox
- Current residual: `docker.openhands.dev/openhands/runtime:latest-nikolaik`
  is not cached on this Mini, so the first sandbox task remains a separate
  explicit step

## Preflight
```bash
python3.12 --version
uv --version
docker --version
df -h / /var/lib/docker
docker system df
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}' | rg 'openhands|REPOSITORY'
ss -ltnp | rg ':3000|:4000|:4031|:4096' || true
```

## Optional operator CLI
The managed runtime does not require the local CLI, but it can still be useful
for operator inspection:
```bash
uv tool install openhands --python 3.12
openhands --version
```

## Install or refresh the managed runtime
```bash
sudo install -d -m 0755 /etc/openhands
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/templates/openhands.env.example \
  /etc/openhands/env
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/systemd/openhands.service \
  /etc/systemd/system/openhands.service
sudo systemctl daemon-reload
sudo systemctl enable --now openhands.service
```

## Local validation
```bash
systemctl is-enabled openhands.service
systemctl is-active openhands.service
journalctl -u openhands.service -n 200 --no-pager
ss -ltnp | rg ':4031'
curl -fsSI http://127.0.0.1:4031/
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg 'openhands-app'
docker inspect openhands-app --format '{{json .HostConfig.Binds}}'
docker inspect openhands-app --format '{{json .Config.Env}}' | jq -r '.[]' | rg '^SANDBOX_VOLUMES='
```

Expected:
- `openhands.service` is `enabled`
- `openhands.service` is `active`
- only `127.0.0.1:4031` is listening
- the root UI responds with `200`
- `docker inspect` shows only:
  - `/var/run/docker.sock`
  - `/home/christopherbailey/.local/share/openhands-phasea:/.openhands`
- `SANDBOX_VOLUMES` carries the disposable workspace contract and is applied
  only when sandbox containers are launched
- no bind includes `/home/christopherbailey/homelab-llm`

## No-LAN-exposure proof
```bash
curl -sS --connect-timeout 2 http://192.168.1.71:4031/ >/dev/null
```

Expected:
- connection fails because the service is loopback-only

## Tailnet operator validation
Validate the dedicated Tailscale Service mapping:
```bash
tailscale serve status --json | jq '.Services["svc:hands"]'
tailscale serve status
```

Expected remote operator URL:
```text
https://hands.tailfd1400.ts.net/
```

Validate from another tailnet node:
```bash
ssh orin 'curl -kI --max-time 10 https://hands.tailfd1400.ts.net/'
ssh orin 'curl -ksS --max-time 10 https://hands.tailfd1400.ts.net/ | sed -n "1,20p"'
```

Expected:
- root returns `HTTP/2 200`
- response body is non-empty HTML

OpenCode boundary:
- OpenCode Web uses dedicated Tailscale Service `svc:codeagent`
- OpenHands work on `svc:hands` must not modify the separate OpenCode mapping

## LiteLLM Phase B gate
Validate the worker contract from inside the app container with the governed key:
```bash
OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)

docker exec -e OPENHANDS_WORKER_KEY="$OPENHANDS_WORKER_KEY" openhands-app sh -lc '
python3 - <<\"PY\"
import json, os, urllib.request, urllib.error

key = os.environ["OPENHANDS_WORKER_KEY"]
bases = [
    "http://host.docker.internal:4000/v1",
    "http://192.168.1.71:4000/v1",
]
tests = {
    "models": ("GET", "/models", None),
    "model_info": ("GET", "/model/info", None),
    "chat_ok": ("POST", "/chat/completions", {
        "model": "code-reasoning",
        "messages": [{"role": "user", "content": "Reply with exactly code-reasoning-ok"}],
        "stream": False,
        "max_tokens": 32
    }),
    "mcp_denied": ("GET", "/mcp/tools", None),
    "responses_denied": ("POST", "/responses", {
        "model": "code-reasoning",
        "input": "hello"
    }),
}
out = {}
for base in bases:
    out[base] = {}
    for name, (method, path, payload) in tests.items():
        req = urllib.request.Request(
            base + path,
            data=(json.dumps(payload).encode() if payload is not None else None),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                out[base][name] = {"status": r.status, "body": r.read().decode()[:800]}
        except urllib.error.HTTPError as e:
            out[base][name] = {"status": e.code, "body": e.read().decode()[:800]}
        except Exception as e:
            out[base][name] = {"error": str(e)}
print(json.dumps(out, indent=2, sort_keys=True))
PY'
```

Expected:
- `GET /v1/models` returns `200` and only `code-reasoning`
- `GET /v1/model/info` returns `200` and populated `code-reasoning` metadata
- `POST /v1/chat/completions` returns `200`
- `GET /v1/mcp/tools` returns `403`
- `POST /v1/responses` returns `403`
- `http://host.docker.internal:4000/v1` is the canonical Phase B path on this
  Mini after authenticated inside-container proof
- `http://192.168.1.71:4000/v1` remains a verified fallback/reference path

## Shadow Qwen-Agent direct provider gate
Validate the preferred direct Qwen-Agent-backed shadow contract from inside the
app container:
```bash
QWEN_AGENT_PROXY_AUTH_TOKEN=$(sudo sed -n 's/^QWEN_AGENT_PROXY_AUTH_TOKEN=//p' /etc/homelab-llm/qwen-agent-proxy.secret.env)

docker exec -e QWEN_AGENT_PROXY_AUTH_TOKEN="$QWEN_AGENT_PROXY_AUTH_TOKEN" openhands-app sh -lc '
python3 - <<\"PY\"
import json, os, urllib.request, urllib.error
key = os.environ["QWEN_AGENT_PROXY_AUTH_TOKEN"]
base = "http://host.docker.internal:4021/v1"
tests = {
    "models": ("GET", "/models", None),
    "model_info": ("GET", "/model/info", None),
    "chat_named": ("POST", "/chat/completions", {
        "model": "qwen-agent-coder-next-shadow",
        "messages": [{"role": "user", "content": "Call noop once with {\\\"value\\\":\\\"x\\\"}."}],
        "tools": [{"type": "function", "function": {"name": "noop", "description": "noop", "parameters": {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"], "additionalProperties": False}}}],
        "tool_choice": {"type": "function", "function": {"name": "noop"}},
        "stream": False,
        "max_tokens": 128
    }),
}
out = {}
for name, (method, path, payload) in tests.items():
    req = urllib.request.Request(
        base + path,
        data=(json.dumps(payload).encode() if payload is not None else None),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out[name] = {"status": r.status, "body": r.read().decode()[:800]}
    except urllib.error.HTTPError as e:
        out[name] = {"status": e.code, "body": e.read().decode()[:800]}
print(json.dumps(out, indent=2, sort_keys=True))
PY'
```

Expected:
- `/models` returns only `qwen-agent-coder-next-shadow`
- `/model/info` succeeds
- named tool call succeeds with populated `tool_calls`

## Optional shadow LiteLLM gate
The LiteLLM shadow path remains useful for operator validation, but it is not
the preferred OpenHands integration path for this slice because worker-key
`/v1/model/info` is still blocked there.

Verify the governed worker contract through LiteLLM only:
```bash
export OPENHANDS_WORKER_KEY="$(cat /home/christopherbailey/.config/openhands/worker_api_key)"
export OPENHANDS_LITELLM_BASE_URL='http://host.docker.internal:4000/v1'

curl -fsS "$OPENHANDS_LITELLM_BASE_URL/models" \
  -H "Authorization: Bearer $OPENHANDS_WORKER_KEY" | jq .

curl -fsS "$OPENHANDS_LITELLM_BASE_URL/model/info" \
  -H "Authorization: Bearer $OPENHANDS_WORKER_KEY" | jq .
```

Expected:
- `code-reasoning` is the only visible worker alias
- worker model info is populated
- OpenHands remains LiteLLM-only for Phase B
- do not configure MCP in OpenHands

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

Do not start this loop casually on the current host state: the runtime sandbox
image is not cached, so the first task execution may trigger a large image pull.

## Joint Qwen-Agent trial
Preferred benchmark repo:
`/home/christopherbailey/openhands-experimental/phase-a-workspace/swebench-micro-001-config-merge`

### Operator setup in the UI
Use the direct Qwen-Agent provider path for this trial:

1. Open `http://127.0.0.1:4031`
2. Set the custom provider/base URL to:
   - `http://host.docker.internal:4021/v1`
3. Set the model to:
   - `qwen-agent-coder-next-shadow`
4. Set the API key to the local bearer token:
```bash
sudo sed -n 's/^QWEN_AGENT_PROXY_AUTH_TOKEN=//p' /etc/homelab-llm/qwen-agent-proxy.secret.env
```
5. Keep the workspace rooted in:
   - `/home/christopherbailey/openhands-experimental/phase-a-workspace/swebench-micro-001-config-merge`

### Task prompt to paste into OpenHands
Use this exact prompt for the first joint trial:

```text
You are working in a small Python repo with a failing unittest suite.

Task:
- Fix the config merge bug so nested overrides merge recursively instead of replacing whole nested dictionaries.
- Do not mutate the input base config while merging.

Requirements:
- Start by explaining the plan briefly.
- Make the smallest correct patch.
- Run `python3 -m unittest`.
- Finish by summarizing the change and the test result.

Do not add dependencies. Keep the fix contained to the existing repo.
```

### Expected validation command
```bash
cd /home/christopherbailey/openhands-experimental/phase-a-workspace/swebench-micro-001-config-merge
python3 -m unittest
```

### Reset between runs
After the OpenHands run and before the Codex run:
```bash
cd /home/christopherbailey/openhands-experimental/phase-a-workspace/swebench-micro-001-config-merge
git reset --hard benchmark-baseline
git clean -fd
python3 -m unittest
```

Expected reset state:
- the repo returns to the intentionally failing baseline
- `python3 -m unittest` fails until the bug is fixed again

### What to save from the OpenHands run
- the final summary text
- the final diff
- the final `python3 -m unittest` output
- any extra files it touched beyond the expected bugfix surface

## Teardown / rollback
```bash
sudo systemctl disable --now openhands.service
sudo rm -f /etc/systemd/system/openhands.service
sudo rm -f /etc/openhands/env
sudo systemctl daemon-reload
sudo docker rm -f openhands-app || true
```

If reverting to a non-managed state, clear `svc:hands` as well so the tailnet
URL does not point at an empty backend:
```bash
tailscale serve clear svc:hands
```
