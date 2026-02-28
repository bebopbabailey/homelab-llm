# 2026-02-27 — websearch-orch Phase 2 tightening (round 2)

## Summary
- Tightened Phase 2 calibration to reduce source starvation without unbounding context size.
- Added fair-share budget logic so later sources receive minimum text slices before total budget exhaustion.
- Reduced loader fanout and raised total budget moderately for better source coverage.

## Repo changes
- Updated `layer-tools/websearch-orch/app/main.py`:
  - Added `EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS`.
  - Added fair-share budget reserve per remaining source in `/web_loader` processing.
- Updated `layer-tools/websearch-orch/config/env.example`:
  - `EXTERNAL_WEB_LOADER_MAX_URLS=12`
  - `EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS=22000`
  - `EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS=600`
- Updated run/validation docs:
  - `layer-tools/websearch-orch/RUNBOOK.md`
  - `docs/foundation/testing.md`
- Updated planning state:
  - `NOW.md`
  - `BACKLOG.md`

## Runtime changes (Mini)
- Backed up `/etc/homelab-llm/websearch-orch.env`:
  - `/etc/homelab-llm/websearch-orch.env.bak.20260227-172853`
- Applied:
  - `EXTERNAL_WEB_LOADER_MAX_URLS=12`
  - `EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS=22000`
  - `EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS=600`
- Restarted:
  - `sudo systemctl restart websearch-orch.service`

## Validation
- `python3 -m py_compile layer-tools/websearch-orch/app/main.py` passed.
- `systemctl is-active websearch-orch.service` => `active`.
- Runtime env confirmed in process environment.
- High-fanout web_loader stress call (18 URLs input):
  - `urls=18 ok=11 errors=1 chars=22000 raw_chars=478214 doc_caps=10 budget_caps=6 budget_drops=0`
- Search-driven pipeline check:
  - `/search` returned 8 reranked results.
  - `/web_loader` on those results:
    - `urls=8 ok=8 errors=0 chars=22000 raw_chars=38179 doc_caps=5 budget_caps=1 budget_drops=0`

## Notes
- This is still Phase 2. No Phase 3 schema/citation contract logic was added.
- Exit remains two consecutive end-user Open WebUI validation passes.
