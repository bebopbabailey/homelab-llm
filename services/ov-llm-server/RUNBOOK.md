# Runbook

## Service control (systemd)
Install the unit and env file:
```bash
sudo mkdir -p /etc/homelab-llm
sudo cp ./ov-server.env /etc/homelab-llm/ov-server.env
sudo cp ./ov-server.service /etc/systemd/system/ov-server.service
sudo systemctl daemon-reload
sudo systemctl enable --now ov-server.service
```

Status and logs:
```bash
systemctl status ov-server.service --no-pager
journalctl -u ov-server.service -n 200 --no-pager
```

## Health checks
```bash
curl -fsS http://127.0.0.1:9000/health | jq .
curl -fsS http://127.0.0.1:9000/v1/models | jq .
```

## Environment
Runtime env lives at `/etc/homelab-llm/ov-server.env`.
Template lives at `ov-server.env` in this repo.

## Model warm-up
See `docs/REFERENCE.md` for warm-up commands and conversion examples.

## Constraints
- Do not touch or restart the existing `ollama` service.
- Do not install system drivers or use global `pip`.
- Use `openvino-genai` for generation.
