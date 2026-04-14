# Runbook: ccproxy-api

## Bootstrap
```bash
cd /home/christopherbailey/homelab-llm/experiments/ccproxy-api
uv venv
.venv/bin/pip install ccproxy-api==0.2.9
```

## Runtime env
Create `/etc/homelab-llm/ccproxy.env` with:
```dotenv
CCPROXY_AUTH_TOKEN=<local-bearer-token>
CCPROXY_API_BASE=http://127.0.0.1:4010/codex/v1
```

## Start/stop
```bash
sudo systemctl start ccproxy-api.service
sudo systemctl stop ccproxy-api.service
sudo systemctl restart ccproxy-api.service
```

## Logs
```bash
journalctl -u ccproxy-api.service -f
```

## Direct validation
```bash
source /etc/homelab-llm/ccproxy.env

curl -fsS -H "Authorization: Bearer ${CCPROXY_AUTH_TOKEN}" \
  http://127.0.0.1:4010/codex/v1/models | jq .

curl -fsS -H "Authorization: Bearer ${CCPROXY_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4010/codex/v1/chat/completions \
  -d '{"model":"gpt-5.3-codex","messages":[{"role":"user","content":"Reply with exactly: ccproxy-chat-ok"}],"stream":false,"max_tokens":32}' | jq .

curl -fsS -H "Authorization: Bearer ${CCPROXY_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4010/codex/v1/responses \
  -d '{"model":"gpt-5.3-codex","input":[{"role":"user","content":"Reply with exactly: ccproxy-responses-ok"}],"max_output_tokens":32}' | jq .
```

Expected:
- `GET /codex/v1/models` returns Codex-family models
- Chat Completions returns non-empty assistant content
- Responses returns a non-empty assistant message in `output`

## Auth checks
```bash
uvx --from ccproxy-api ccproxy auth status codex
```

Expected:
- authenticated Codex provider with a live subscription on the current account
