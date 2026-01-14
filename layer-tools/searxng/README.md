# SearXNG

## Overview
SearXNG is a privacy-focused metasearch engine. It is implemented as a **local
search endpoint** for tools/agents and must not be LAN-exposed without approval.

Upstream project: `https://github.com/searxng/searxng`
Docs: `https://docs.searxng.org/admin/installation.html`

## Constraints
- No Docker installs in this repo.
- Bind to localhost unless explicitly approved for LAN exposure.
- Use `uv` for Python dependency management.

## Install (no Docker, repo-based)
SearXNG runs from `layer-tools/searxng/app` and is managed via systemd.

1) Clone upstream into the service directory:

```bash
git clone https://github.com/searxng/searxng.git layer-tools/searxng/app
```

2) Bootstrap dependencies + settings:

```bash
./layer-tools/searxng/scripts/bootstrap.sh
```

This will:
- create `layer-tools/searxng/app/.venv`
- install `requirements.txt` + `requirements-server.txt`
- write `/etc/searxng/settings.yml` from `layer-tools/searxng/settings.yml.example`
- write `/etc/searxng/env` from `layer-tools/searxng/searxng.env.example`

## Configuration (essentials)
Key settings in `/etc/searxng/settings.yml`:
- `server.secret_key` (required)
- `server.bind_address` (default `127.0.0.1`)
- `server.port` (default `8888`)
- `search.formats` (include `json` for API use)
- `search.safe_search` (0/1/2)
- `search.autocomplete` (optional)
- `server.limiter` (local-only rate limiting)

Useful knobs for future tuning:
- `server.base_url` (stable links in results)
- `search.languages` or `search.language`
- `engines` (disable unused engines to speed up results)
- `outgoing.request_timeout` (reduce slow engine hangs)

SearXNG reads its config from `SEARXNG_SETTINGS_PATH`. Example:

```bash
export SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml
```

## Run (systemd)
Install the unit and start:

```bash
sudo cp /home/christopherbailey/homelab-llm/platform/ops/systemd/searxng.service /etc/systemd/system/searxng.service
sudo systemctl daemon-reload
sudo systemctl enable --now searxng.service
```

## Usage
Once running on localhost:
- Web UI: `http://127.0.0.1:8888`
- JSON search endpoint: `http://127.0.0.1:8888/search?q=<query>&format=json`

## LiteLLM Integration
LiteLLM exposes SearXNG via `/v1/search/<tool_name>` once configured in
`layer-gateway/litellm-orch/config/router.yaml`.
Set these in `layer-gateway/litellm-orch/config/env.local`:
- `SEARXNG_API_BASE=http://127.0.0.1:8888`
- `SEARXNG_API_KEY=` (optional)

## References
- Installation: `https://docs.searxng.org/admin/installation.html`
- Settings: `https://docs.searxng.org/admin/settings/index.html`
