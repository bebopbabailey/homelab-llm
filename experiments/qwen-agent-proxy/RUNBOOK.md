# Runbook: qwen-agent-proxy

## Runtime files
- Repo-managed unit: `platform/ops/systemd/qwen-agent-proxy.service`
- Non-secret env template: `platform/ops/templates/qwen-agent-proxy.env.example`
- Local secret env: `/etc/homelab-llm/qwen-agent-proxy.secret.env`

## Install / refresh
```bash
sudo install -d -m 0755 /etc/homelab-llm
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/templates/qwen-agent-proxy.env.example \
  /etc/homelab-llm/qwen-agent-proxy.env
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/systemd/qwen-agent-proxy.service \
  /etc/systemd/system/qwen-agent-proxy.service
sudo systemctl daemon-reload
sudo systemctl enable --now qwen-agent-proxy.service
```

## Logs
```bash
journalctl -u qwen-agent-proxy.service -f
```

## Health
```bash
source /etc/homelab-llm/qwen-agent-proxy.secret.env
curl -fsS http://127.0.0.1:4021/health | jq .
curl -fsS -H "Authorization: Bearer ${QWEN_AGENT_PROXY_AUTH_TOKEN}" \
  http://127.0.0.1:4021/v1/models | jq .
```

When OpenHands must call the sidecar from inside `openhands-app`, set:
```bash
sudo python3 - <<'PY'
from pathlib import Path
path = Path('/etc/homelab-llm/qwen-agent-proxy.env')
text = path.read_text()
text = text.replace('QWEN_AGENT_PROXY_HOST=127.0.0.1', 'QWEN_AGENT_PROXY_HOST=172.17.0.1')
path.write_text(text)
PY
systemctl --user restart qwen-agent-proxy-shadow.service
```

This keeps the listener on the Docker bridge only, so the app container can
reach it through `http://host.docker.internal:4021` without exposing it on the
LAN.

## Studio backend preflight
Current accepted shadow target:
- model artifact: `mlx-community/Qwen3-Coder-Next-4bit`
- port: `8134`
- model name: `mlx-qwen3-coder-next-4bit-shadow`
- Mini-local tunnel target: `127.0.0.1:18134 -> studio:127.0.0.1:8134`

Known local repair:
- If tokenizer construction fails, patch the local model snapshot
  `tokenizer_config.json` so `extra_special_tokens` is a mapping instead of a list.

Launch shape used for validation:
```bash
ssh studio 'bash -lc '"'"'
source ~/.venv-vllm-metal/bin/activate >/dev/null 2>&1
RUN_DIR=/tmp/qwen3-coder-next-shadow-8134
mkdir -p "$RUN_DIR"
nohup vllm serve /Users/thestudio/models/hf/models--mlx-community--Qwen3-Coder-Next-4bit/snapshots/7b9321eabb85ce79625cac3f61ea691e4ea984b5 \
  --host 127.0.0.1 \
  --port 8134 \
  --served-model-name mlx-qwen3-coder-next-4bit-shadow \
  --max-model-len 32768 \
  --generation-config vllm \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --no-async-scheduling \
  >"$RUN_DIR/stdout.log" 2>"$RUN_DIR/stderr.log" < /dev/null &
echo $! > "$RUN_DIR/pid"
'"'"''
```

Create the Mini-local tunnel before starting the proxy:
```bash
ssh -f -N -M -S /tmp/qwen-agent-coder-next-8134.sock \
  -L 18134:127.0.0.1:8134 \
  -o ExitOnForwardFailure=yes \
  studio
```

## Direct tool-call smoke
```bash
source /etc/homelab-llm/qwen-agent-proxy.secret.env

curl -fsS http://127.0.0.1:4021/v1/chat/completions \
  -H "Authorization: Bearer ${QWEN_AGENT_PROXY_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen-agent-coder-next-shadow",
    "messages":[{"role":"user","content":"Call noop once with {\"value\":\"x\"}."}],
    "tools":[{"type":"function","function":{"name":"noop","description":"noop","parameters":{"type":"object","properties":{"value":{"type":"string"}},"required":["value"],"additionalProperties":false}}}],
    "tool_choice":{"type":"function","function":{"name":"noop"}},
    "stream":false,
    "max_tokens":128
  }' | jq .
```

## OpenHands container-path smoke
```bash
TOKEN=$(sudo sed -n 's/^QWEN_AGENT_PROXY_AUTH_TOKEN=//p' /etc/homelab-llm/qwen-agent-proxy.secret.env)

docker exec -e QWEN_AGENT_PROXY_AUTH_TOKEN="$TOKEN" openhands-app sh -lc '
python3 - <<\"PY\"
import json, os, urllib.request, urllib.error
base = "http://host.docker.internal:4021/v1"
key = os.environ["QWEN_AGENT_PROXY_AUTH_TOKEN"]
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
        with urllib.request.urlopen(req, timeout=60) as r:
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

Expected:
- `finish_reason` is `tool_calls`
- one populated `tool_calls` entry is returned
- `function.arguments` is valid JSON

## Teardown / rollback
```bash
sudo systemctl disable --now qwen-agent-proxy.service
sudo rm -f /etc/systemd/system/qwen-agent-proxy.service
sudo rm -f /etc/homelab-llm/qwen-agent-proxy.env
sudo rm -f /etc/homelab-llm/qwen-agent-proxy.secret.env
sudo systemctl daemon-reload
```
