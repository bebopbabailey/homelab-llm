# 2026-03-07 — websearch supported-path reset

## Summary
- Removed the custom LiteLLM web-search schema path and deleted `fast-research`.
- Removed `websearch-orch` from active deployment and deleted its tracked repo tree.
- Cut Open WebUI back to documented native SearXNG + `safe_web` configuration with explicit env-backed result-count, concurrency, and filter controls.
- Rewrote docs and runbooks to codify the ownership boundary:
  - Open WebUI owns web-search UX plus provider/loader configuration.
  - LiteLLM owns routing/auth/retries/fallbacks and generic `/v1/search/<tool_name>` access only.
  - vLLM owns inference and explicit structured decoding only when requested.

## Why
The repo had drifted into custom web-search glue spread across Open WebUI prompt assumptions, LiteLLM schema middleware, and a custom `websearch-orch` service. The supported-path reset intentionally deletes that stack instead of preserving compatibility.

## Runtime cutover
- Open WebUI now uses:
  - `WEB_SEARCH_ENGINE=searxng`
  - `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`
  - `WEB_SEARCH_RESULT_COUNT=6`
  - `WEB_SEARCH_CONCURRENT_REQUESTS=1`
  - `WEB_LOADER_ENGINE=safe_web`
  - `WEB_LOADER_TIMEOUT=15`
  - `WEB_LOADER_CONCURRENT_REQUESTS=2`
  - explicit `WEB_FETCH_FILTER_LIST`
  - explicit `WEB_SEARCH_DOMAIN_FILTER_LIST`
- `ENABLE_PERSISTENT_CONFIG=False` remains set, so env/drop-ins are authoritative and Admin UI changes do not persist across restart.

## Intentional removals
- no `websearch_schema_guardrail`
- no `web_answer` schema contract in LiteLLM
- no prompt-shape coupling to `<source id=`
- no `fast-research` alias
- no active `websearch-orch` policy engine, loader, or deployment wiring

## Validation focus
- LiteLLM readiness no longer reports `WebsearchSchemaGuardrail`.
- Open WebUI service env points to SearXNG `:8888` with `safe_web`.
- `websearch-orch.service` is disabled/removed.
- Open WebUI end-to-end web-search smoke succeeds on the supported path.
