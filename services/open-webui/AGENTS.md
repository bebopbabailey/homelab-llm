# Agent Guidance: Open WebUI

## Scope
Maintain the Open WebUI service boundary only.

## Read First
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Key files
- Systemd unit: `/etc/systemd/system/open-webui.service`
- Env: `/etc/open-webui/env`

## Run
```bash
sudo systemctl restart open-webui.service
journalctl -u open-webui.service -f
```
