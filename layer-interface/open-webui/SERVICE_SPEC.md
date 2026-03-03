# Service Spec: Open WebUI

## Purpose
Human-facing UI for LLM interactions routed through LiteLLM.

## Interface
- HTTP UI: `0.0.0.0:3000` (LAN + tailnet exposure in current deployment)
- Health: `GET /health`

## Dependencies
- LiteLLM proxy at `http://127.0.0.1:4000/v1`
- SearXNG-compatible search endpoint at `SEARXNG_QUERY_URL` (currently
  `http://127.0.0.1:8899/search?q=<query>`)
- External web-loader endpoint for page extraction when
  `WEB_LOADER_ENGINE=external` (currently `http://127.0.0.1:8899/web_loader`)

## Configuration
- `/etc/open-webui/env` (systemd EnvironmentFile)
- `/etc/systemd/system/open-webui.service.d/*.conf` (web-search and loader
  overrides)
- Data stored in `/home/christopherbailey/.open-webui`
