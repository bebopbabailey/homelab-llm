# 2026-02-18 — websearch-orch hygiene proxy for Open WebUI web search

## Summary
- Added a localhost-only `websearch-orch` service to improve web-search source
  quality before synthesis in Open WebUI.
- The proxy keeps SearXNG JSON compatibility while dropping low-signal results
  (empty, blocked pattern, malformed URL, domain-capped, duplicate URL).

## Implementation
- New service code: `layer-tools/websearch-orch/app/main.py` (stdlib-only).
- New ops docs:
  - `layer-tools/websearch-orch/AGENTS.md`
  - `layer-tools/websearch-orch/RUNBOOK.md`
  - `layer-tools/websearch-orch/config/env.example`
- Added test commands under `docs/foundation/testing.md`.

## Runtime wiring
- systemd service:
  - `/etc/systemd/system/websearch-orch.service`
  - env file `/etc/homelab-llm/websearch-orch.env`
  - bind `127.0.0.1:8899`
- Open WebUI drop-in:
  - `/etc/systemd/system/open-webui.service.d/30-websearch-orch.conf`
  - `SEARXNG_QUERY_URL=http://127.0.0.1:8899/search?q=<query>`

## Notes
- This is Phase 1 hygiene only (no reranker yet).
- Behavior is reversible by removing the Open WebUI drop-in and stopping
  `websearch-orch.service`.
