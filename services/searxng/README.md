# SearXNG (planned)

## Overview
SearXNG is a privacy-focused metasearch engine. It is planned as a **local
search endpoint** for tools/agents and must not be LAN-exposed without approval.

Upstream project: `https://github.com/searxng/searxng`
Docs: `https://docs.searxng.org/admin/installation.html`

## Constraints
- No Docker installs in this repo.
- Bind to localhost unless explicitly approved for LAN exposure.
- Use `uv` for Python dependency management.

## Install (manual, no Docker)
The upstream project provides install scripts and step-by-step setup. For a
manual install that aligns with `uv`:

1) Create a dedicated user (recommended by upstream) and a system directory
   (example: `/opt/searxng`).
2) Clone the repo and create a virtual environment:

```bash
git clone https://github.com/searxng/searxng.git /opt/searxng
cd /opt/searxng
uv venv .venv
uv pip install -r requirements.txt
```

3) Create `/etc/searxng/settings.yml` based on the upstream template and set
   `server.secret_key`. The upstream template lives in:
   `utils/templates/etc/searxng/settings.yml`.

## Configuration (essentials)
Key settings in `/etc/searxng/settings.yml`:
- `server.secret_key` (required)
- `server.bind_address` (default `127.0.0.1`)
- `server.port` (default `8888`)

SearXNG reads its config from `SEARXNG_SETTINGS_PATH`. Example:

```bash
export SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml
```

## Run (local)
For a local dev run, the upstream `manage` script supports `webapp.run` and
uses Granian/WSGI for development. For production, follow the upstream uWSGI or
Granian guides.

## Usage
Once running on localhost:
- Web UI: `http://127.0.0.1:8888`
- JSON search endpoint: `http://127.0.0.1:8888/search?q=<query>&format=json`

## References
- Installation: `https://docs.searxng.org/admin/installation.html`
- Settings: `https://docs.searxng.org/admin/settings/index.html`
