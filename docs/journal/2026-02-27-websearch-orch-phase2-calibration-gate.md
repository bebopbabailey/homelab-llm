# 2026-02-27 — websearch-orch Phase 2 calibration gate implementation

## Summary
- Implemented Phase 2 extraction-size controls in `websearch-orch` to reduce oversized
  Open WebUI retrieval context while preserving fail-open behavior.
- Added structured telemetry to make calibration measurable from `journalctl`.
- Applied conservative runtime caps on Mini and validated with live service checks.

## Repo changes
- Updated `layer-tools/websearch-orch/app/main.py`:
  - Added `EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS` env control.
  - Split per-document cap vs total-response cap behavior.
  - Added metadata fields: `raw_char_count`, `doc_char_truncated`, `budget_char_truncated`,
    `budget_char_limit`, `budget_remaining_after`.
  - Expanded `web_loader` telemetry log to include:
    `chars`, `raw_chars`, `doc_caps`, `budget_caps`, `budget_drops`, `remaining_budget`.
- Updated `layer-tools/websearch-orch/config/env.example` with Phase 2 recommended values:
  - `EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS=3500`
  - `EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS=18000`
- Updated `layer-tools/websearch-orch/RUNBOOK.md` with Phase 2 verification commands.
- Updated `docs/foundation/testing.md` with Phase 2 calibration checks and pass guidance.

## Runtime wiring (Mini)
- Backed up env file:
  - `/etc/homelab-llm/websearch-orch.env.bak.20260227-154415`
- Applied runtime caps in `/etc/homelab-llm/websearch-orch.env`:
  - `EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS=3500`
  - `EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS=18000`
- Restarted service:
  - `sudo systemctl restart websearch-orch.service`

## Validation evidence
- `python3 -m py_compile layer-tools/websearch-orch/app/main.py` passed.
- `systemctl is-active websearch-orch.service` => `active`.
- `curl -fsS http://127.0.0.1:8899/health | jq .` => `ok: true`.
- Search smoke:
  - `curl -fsS "http://127.0.0.1:8899/search?q=beginner+wok+cooking+tips&format=json"`
  - returned `result_count: 8`.
- Web-loader smoke:
  - 3 successful documents returned from 4 URLs.
  - Example metadata shows cap behavior:
    - Wikipedia wok page: `raw_char_count=26995`, `char_count=3500`, `doc_char_truncated=true`.
- Log telemetry confirmed:
  - `web_loader urls=4 ok=3 errors=1 chars=6858 raw_chars=30353 doc_caps=1 budget_caps=0 budget_drops=0 remaining_budget=11142`

## Notes
- No new LAN exposure or port changes.
- Phase 2 remains **active (validation)** until end-user Open WebUI runs pass baseline gates
  in consecutive checks.
