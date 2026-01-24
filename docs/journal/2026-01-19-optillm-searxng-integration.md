# 2026-01-19 — OptiLLM web_search uses SearXNG

## Summary
Patched OptiLLM `web_search` to use SearXNG when available, avoiding Selenium.

## Changes
- `web_search` plugin now checks `SEARXNG_API_BASE` and calls SearXNG JSON API.
- Falls back to Selenium/Google only if SearXNG is not configured.
- Added `SEARXNG_API_BASE=http://127.0.0.1:8888` to `/etc/optillm-proxy/env`.

## Files
- `layer-gateway/optillm-proxy/.venv/lib/python3.11/site-packages/optillm/plugins/web_search_plugin.py`
- `/etc/optillm-proxy/env`
- `layer-gateway/optillm-proxy/README.md`
- `layer-gateway/optillm-proxy/SERVICE_SPEC.md`
- `layer-gateway/optillm-proxy/docs/FEATURES.md`
- `docs/INTEGRATIONS.md`
