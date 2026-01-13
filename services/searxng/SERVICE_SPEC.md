# Service Spec: searxng

## Purpose
Provide a local search endpoint for agents/tools. No direct LAN exposure
without explicit approval.

## Runtime
- **Language**: Python 3.x (upstream supports 3.10+)
- **Dependency manager**: `uv` only
- **Process model**: long-running web app (WSGI)
- **App dir**: `services/searxng/app`
- **Systemd unit**: `/etc/systemd/system/searxng.service`

## Network
- **Bind address**: 127.0.0.1 (default)
- **Port**: 8888 (default)
- **External access**: forbidden until approved

## Endpoints (default)
- Web UI: `/`
- JSON search: `/search?q=<query>&format=json`
- Metrics (optional): `/metrics` (if enabled)

## Configuration
- Settings file: `/etc/searxng/settings.yml`
- Environment: `SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml`
- Required: `server.secret_key`
- Search formats must include `json` for API usage.

## LiteLLM Integration
- Add a `search_tools` entry for SearXNG in
  `services/litellm-orch/config/router.yaml`.
- Use `/v1/search/<tool_name>` for clients to query via LiteLLM.
- Tool name: `searxng-search`.

## References
- Upstream: `https://github.com/searxng/searxng`
- Installation: `https://docs.searxng.org/admin/installation.html`
- Settings: `https://docs.searxng.org/admin/settings/index.html`
