# 2026-03-03 — Open WebUI web-search JSONResponse hardening

## Summary
Patched the Open WebUI middleware runtime to handle non-dict completion payloads returned from query generation during web search.

This fixes the observed crash:
- `TypeError: 'JSONResponse' object is not subscriptable`
- path: `open_webui/utils/middleware.py` in `chat_web_search_handler`

## What changed
- Runtime file patched:
  - `layer-interface/open-webui/.venv/lib/python3.12/site-packages/open_webui/utils/middleware.py`
- Added helper functions:
  - `_parse_json_object(...)`
  - `_normalize_completion_payload(...)`
  - `_extract_first_choice_content(...)`
- Applied normalization in both query-generation paths:
  - `chat_web_search_handler(...)`
  - `chat_completion_files_handler(...)`
- Added explicit exception context log in web-search query generation path.
- Backup created before patch:
  - `.../middleware.py.bak.20260303000820`

## Verification
- `python -m py_compile` on patched middleware file succeeded.
- `sudo systemctl restart open-webui.service` succeeded.
- `open-webui.service` is active after restart.
- Immediate post-restart journal grep showed no fresh `JSONResponse object is not subscriptable` errors.

## Notes
- This is a runtime venv hotfix for service restoration.
- No API contract changes for clients; this only hardens middleware payload handling.
- End-user validation should now re-run the Phase 2 prompt pack and confirm no middleware traceback recurrence.
