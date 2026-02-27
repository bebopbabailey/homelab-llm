# 2026-02-21 — websearch-orch local reranker (Phase 1)

## Summary
- Added a local semantic reranker stage to `websearch-orch` while preserving
  SearXNG-compatible output shape for Open WebUI.
- Kept fail-open behavior: if reranker init/inference fails, the service
  returns filtered baseline ranking instead of failing requests.

## Implementation
- Updated `layer-tools/websearch-orch/app/main.py`:
  - new env-driven reranker controls (`RERANK_*`)
  - optional `flashrank`-backed ranking path
  - structured logs for `rerank=True|False` and `top_scores`
  - fallback to filtered baseline on reranker failure
- Updated `layer-tools/websearch-orch/config/env.example` with reranker keys.
- Updated `layer-tools/websearch-orch/requirements.txt`:
  - `flashrank==0.2.10`
- Updated `layer-tools/websearch-orch/RUNBOOK.md` with dependency sync and
  reranker verification commands.

## Runtime wiring
- Created isolated service runtime via venv:
  - `/home/christopherbailey/homelab-llm/layer-tools/websearch-orch/.venv`
- Added systemd drop-in:
  - `/etc/systemd/system/websearch-orch.service.d/10-venv-runtime.conf`
  - overrides `ExecStart` to use venv Python
- Enabled reranking in:
  - `/etc/homelab-llm/websearch-orch.env`
  - `RERANK_ENABLED=true`
  - `RERANK_MODEL=ms-marco-TinyBERT-L-2-v2`

## Validation
- `python3 -m py_compile layer-tools/websearch-orch/app/main.py` passed.
- `systemctl status websearch-orch.service` confirms venv runtime active.
- `curl http://127.0.0.1:8899/health` returns `ok: true`.
- Search smoke tests return expected count (`8`) and logs show reranker active:
  - `rerank=True`
  - `top_scores=[(...)]`

## Notes
- No new LAN exposure or port changes; service remains `127.0.0.1:8899`.
- Open WebUI integration remains unchanged:
  `SEARXNG_QUERY_URL=http://127.0.0.1:8899/search?q=<query>`.
