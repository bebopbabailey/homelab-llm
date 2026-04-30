# Open WebUI

## Overview
Open WebUI is the human-facing UI for the homelab. It talks to LiteLLM and exposes
a browser UI on port 3000.

It also supports native Knowledge collections backed by the Studio retrieval
stack:
- Elasticsearch through a Mini-local localhost bridge
- embeddings through `vector-db /v1/embeddings`

## Key paths
- Systemd unit: `/etc/systemd/system/open-webui.service`
- Bridge unit: `/etc/systemd/system/open-webui-elasticsearch-bridge.service`
- Env file: `/etc/open-webui/env`
- Data: `/home/christopherbailey/.open-webui`
- Venv: `/home/christopherbailey/homelab-llm/services/open-webui/.venv`

## Run (systemd)
```bash
sudo systemctl enable --now open-webui.service
```

## Health
```bash
curl http://127.0.0.1:3000/health
```

## Knowledge backend runtime helpers
- Bridge unit template:
  `services/open-webui/systemd/open-webui-elasticsearch-bridge.service`
- Backend sync drop-in:
  `services/open-webui/systemd/80-knowledge-backend-sync.conf`
- UI reflection helper:
  `services/open-webui/scripts/openwebui_knowledge_sync.py`
