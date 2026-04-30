# 2026-04-27 — Open WebUI web-search first-pass tuning

## Objective
- Reduce native Open WebUI web-search retrieval fanout on Mini without
  reviving the retired custom proxy stack.
- Limit this pass to the two safest documented knobs: result count and loader
  timeout.

## Runtime shape
- Host: Mini
- Service: `open-webui.service`
- Search backend: local SearXNG `http://127.0.0.1:8888/search?q=<query>&format=json`
- Loader: native Open WebUI `safe_web`
- Edited live drop-in: `/etc/systemd/system/open-webui.service.d/20-websearch-baseline.conf`

## Change
- `WEB_SEARCH_RESULT_COUNT=6` -> `4`
- `WEB_LOADER_TIMEOUT=15` -> `10`

Backup created before edit:
- `/etc/systemd/system/open-webui.service.d/20-websearch-baseline.conf.bak.20260427T235258Z`

## Validation
- Restarted Open WebUI cleanly after `daemon-reload`.
- `systemctl is-active open-webui.service` returned `active`.
- `curl -fsS http://127.0.0.1:3000/health | jq .` returned `{"status": true}`.
- Verified live env:
  - `WEB_SEARCH_RESULT_COUNT=4`
  - `WEB_LOADER_TIMEOUT=10`

Controlled before/after probe:
- Same OWUI API request before and after change:
  - model: `fast`
  - `features.web_search=true`
  - prompt: `Find current SearXNG documentation about improving search relevance and summarize the main tuning knobs in 5 bullets.`
- Before change:
  - response completed with `sources_count=1`
  - Open WebUI logs showed `embeddings generated 33 for 33 items`
- After change:
  - response completed with `sources_count=1`
  - Open WebUI logs showed `embeddings generated 26 for 26 items`

## Outcome
- First-pass tuning succeeded.
- The supported Open WebUI -> SearXNG -> `safe_web` path remained healthy.
- The controlled probe reduced temporary retrieval fanout from `33` to `26`
  embedded items, about a 21% drop for the same query.

## Notes
- This was a narrow runtime tuning pass only; no SearXNG engine tuning or
  custom retrieval middleware was introduced.
- Result quality remains mixed because native Open WebUI still lacks reranking,
  trust-tiering, and explicit total-text budgets.

## Cleanup state
- No rollback required after validation.
- Rollback path is to restore the backup drop-in above, reload systemd, and
  restart `open-webui.service`.
