# Open WebUI

## Overview
Open WebUI is the human-facing UI for the homelab. It talks to LiteLLM and exposes
a browser UI on port 3000.

## Key paths
- Systemd unit: `/etc/systemd/system/open-webui.service`
- Env file: `/etc/open-webui/env`
- Data: `/home/christopherbailey/.open-webui`
- Venv: `/home/christopherbailey/homelab-llm/layer-interface/open-webui/.venv`

## Run (systemd)
```bash
sudo systemctl enable --now open-webui.service
```

## Health
```bash
curl http://127.0.0.1:3000/health
```
