# 2026-05-01 — SearXNG reliability-first hardening

## Objective
- Keep the supported Mini-hosted `Open WebUI -> SearXNG -> safe_web` path
  unchanged while reducing the number of ambiguous research searches that die
  with `No results found from web search`.
- Preserve the earlier month-name and zero-overlap junk protections, but stop
  treating every strict-filter miss as a hard failure.

## Runtime shape
- Host: Mini
- Services:
  - `open-webui.service`
  - `searxng.service`
- Search backend: `http://127.0.0.1:8888/search?q=<query>&format=json`
- Loader: native Open WebUI `safe_web`
- Runtime hotfix path:
  - `open_webui/utils/middleware.py`
  - `open_webui/routers/retrieval.py`

## Changes
- Repo:
  - updated `scripts/openwebui_querygen_hotfix.py` so retrieval hardening now
    keeps a bounded low-confidence fallback set when strict lexical-overlap
    filtering produces no strong or weak hits
  - extended `scripts/tests/test_openwebui_querygen_hotfix.py` to cover the
    new retrieval fallback and the upgrade path from the prior hard-fail patch
  - added web-search regression fixtures for month/community ambiguity and a
    paired official-docs sanity query in `evals/websearch/queries.jsonl`
  - updated Open WebUI runtime docs and shared testing notes to reflect the new
    fallback behavior
- Live host:
  - reran `scripts/openwebui_querygen_hotfix.py` against the installed Open
    WebUI runtime so the retrieval patch landed immediately
  - restarted `open-webui.service`
- SearXNG host config:
  - no engine or bind changes in this pass

## Validation
- Repo checks:
  - `python3 -m py_compile scripts/openwebui_querygen_hotfix.py`
  - `uv run python -m unittest scripts.tests.test_openwebui_querygen_hotfix`
- Runtime patch application:
  - `python3 scripts/openwebui_querygen_hotfix.py --target .../middleware.py --backup-dir .../utils`
  - verified both runtime markers after patch
- Service health:
  - `open-webui.service` active after restart
  - `searxng.service` remained active; no restart required
- Search-path checks:
  - direct SearXNG JSON smoke still returns ordinary results for neutral queries
  - the known month/community prompt now returns a bounded source set instead of
    failing with `No results found from web search`

## Outcome
- The supported search path remains native Open WebUI + local SearXNG.
- The system still prefers strict overlap matches, but ambiguous research
  prompts now degrade gracefully when only weak or low-confidence results are
  available.
- This does not solve SearXNG engine ranking quality by itself; it only makes
  the OWUI-side handling less brittle while the engine substrate is improved
  separately.

## Cleanup state
- No rollback performed.
- Rollback path:
  - restore the runtime backups produced by `scripts/openwebui_querygen_hotfix.py`
  - rerun the prior patch if needed
  - restart `open-webui.service`
