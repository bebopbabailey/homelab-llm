# Service Spec: searxng (planned)

## Purpose
Provide a local search endpoint for agents/tools. No direct LAN exposure
without explicit approval.

## Runtime
- **Language**: Python 3.x (upstream supports 3.10+)
- **Dependency manager**: `uv` only
- **Process model**: long-running web app (WSGI/ASGI)

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

## References
- Upstream: `https://github.com/searxng/searxng`
- Installation: `https://docs.searxng.org/admin/installation.html`
- Settings: `https://docs.searxng.org/admin/settings/index.html`
