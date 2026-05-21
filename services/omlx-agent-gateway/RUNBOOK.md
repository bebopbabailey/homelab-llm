# Runbook: omlx-agent-gateway

## Runtime Files
- Repo unit: `platform/ops/systemd/omlx-agent-gateway.service`
- Installed unit: `/etc/systemd/system/omlx-agent-gateway.service`
- Non-secret env: `/etc/homelab-llm/omlx-agent-gateway.env`
- Secret env: `/etc/homelab-llm/omlx-agent-gateway.secret.env`

## Install Or Refresh
```bash
sudo install -d -m 0755 /etc/homelab-llm
sudo install -m 0644 platform/ops/templates/omlx-agent-gateway.env.example \
  /etc/homelab-llm/omlx-agent-gateway.env
sudo install -m 0644 platform/ops/systemd/omlx-agent-gateway.service \
  /etc/systemd/system/omlx-agent-gateway.service
sudo systemctl daemon-reload
sudo systemctl enable --now omlx-agent-gateway.service
```

## Health
```bash
curl -fsS http://127.0.0.1:4022/health | jq .
curl -fsS http://127.0.0.1:4022/v1/models | jq .
curl -fsS http://127.0.0.1:4022/v1/model/info | jq .
```

## Notes
- Keep the Studio API key and optional gateway bearer token in the secret env.
- The sidecar remains localhost-only; do not expose it through Tailscale, LiteLLM,
  Open WebUI, or OpenHands in this slice.

