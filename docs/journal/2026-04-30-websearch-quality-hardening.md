# 2026-04-30 — OWUI web-search quality hardening

## Objective
- Harden the supported Open WebUI -> SearXNG -> `safe_web` path on Mini
  without reviving `websearch-orch` or changing any ports/binds.
- Reduce month-name and one-token brand collisions that were polluting loaded
  sources for community-sentiment web searches.

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
  - extended `scripts/openwebui_querygen_hotfix.py` so restart-time patching now
    normalizes generated rewrites and adds a narrow retrieval hygiene pass
  - updated Open WebUI and SearXNG service docs plus platform canon
- Live host:
  - `/etc/systemd/system/open-webui.service.d/20-websearch-baseline.conf`
    changed `WEB_SEARCH_RESULT_COUNT=4` -> `3`
  - `/etc/searxng/settings.yml`
    - `mojeek` -> disabled
    - added explicit disables for `karmasearch`, `karmasearch videos`, and
      `karmasearch news`
  - manually ran the new hotfix script once against the installed Open WebUI
    runtime before restart so retrieval hygiene landed immediately

Backups created before host edits:
- `/etc/searxng/settings.yml.bak.20260430T031419Z`
- `/etc/systemd/system/open-webui.service.d/20-websearch-baseline.conf.bak.20260430T031419Z`
- Open WebUI runtime backups were created by `scripts/openwebui_querygen_hotfix.py`

## Unexpected runtime repair
- Restarting `searxng.service` exposed a stale shebang in
  `services/searxng/app/.venv/bin/granian` pointing at the deleted
  `homelab-llm-searxng-runtime-recovery` worktree.
- Repaired the launcher in place to point at the canonical local venv:
  `#!/home/christopherbailey/homelab-llm/services/searxng/app/.venv/bin/python3`
- After the repair, `searxng.service` restarted cleanly.

## Validation
- Repo checks:
  - `python3 -m py_compile scripts/openwebui_querygen_hotfix.py`
  - `uv run python -m unittest scripts.tests.test_openwebui_querygen_hotfix`
  - `/home/christopherbailey/homelab-llm/layer-interface/open-webui/.venv/bin/python -m unittest services.open-webui.tests.test_chatgpt5_terminal_default`
- Service health:
  - `open-webui.service` active after restart
  - `searxng.service` active after restart and launcher repair
- Marker checks:
  - middleware marker present:
    `querygen-hardening: avoid poisoned queries fallback; normalize generated search queries`
  - retrieval marker present:
    `web-search-result-hygiene: drop low-overlap junk before fetch`
- Direct SearXNG smoke:
  - `curl -fsS "http://127.0.0.1:8888/search?q=openwebui+searxng&format=json"`
    returned 10 results with GitHub/Open WebUI first
- Neutral end-to-end OWUI smoke:
  - prompt: `Search the web for two recent Open WebUI and SearXNG references and summarize them in two bullets.`
  - completed with a populated `sources` entry backed by SearXNG docs/Wikipedia
- Pathological regression case:
  - prompt: `What is sentiment on junior developer demand in April 2026 based on community forums?`
  - direct SearXNG still ranks `APRIL` insurance pages for the raw query
  - OWUI now fails closed with `No results found from web search` instead of
    embedding irrelevant `APRIL` / `Junior Einstein` pages into retrieval

## Outcome
- Hardening succeeded for the supported path:
  - ordinary search still works
  - the known bad collision case no longer pollutes retrieved context
- The underlying SearXNG relevance issue for certain month/community queries is
  not fully solved at the engine layer; the current mitigation is a safer
  OWUI-side failure mode rather than pretending low-quality hits are usable.

## Cleanup state
- No rollback performed.
- Rollback path:
  - restore the two `/etc` backups above
  - restore the pre-patch Open WebUI runtime backups if needed
  - restart `searxng.service` and `open-webui.service`
