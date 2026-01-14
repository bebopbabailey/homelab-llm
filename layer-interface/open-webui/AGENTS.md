# Agent Guidance: Open WebUI

## Scope
Keep changes minimal; this directory primarily hosts the venv and service wiring.

## Key files
- Systemd unit: `/etc/systemd/system/open-webui.service`
- Env: `/etc/open-webui/env`

## Run
```bash
sudo systemctl restart open-webui.service
journalctl -u open-webui.service -f
```
