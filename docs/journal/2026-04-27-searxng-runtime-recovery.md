# 2026-04-27 — SearXNG runtime recovery

## Objective
- Restore the supported Mini web-search path after the live `searxng.service`
  drifted to a deleted repo path and stopped serving `127.0.0.1:8888`.
- Keep the March 7 supported-path reset intact: no `websearch-orch` revival,
  no LiteLLM schema middleware, and no new exposure.

## Initial evidence
- `systemctl status searxng.service --no-pager` showed a restart loop with
  `status=203/EXEC`.
- `systemctl cat searxng.service` pointed at
  `/home/christopherbailey/homelab-llm/layer-tools/searxng/app`.
- `platform/ops/systemd/searxng.service` points at
  `/home/christopherbailey/homelab-llm/services/searxng/app`.
- `curl http://127.0.0.1:8888/search?...&format=json` failed.
- LiteLLM `POST /v1/search/searxng-search` returned `500` because it could not
  connect to `127.0.0.1:8888`.
- `/etc/homelab-llm/mcp-registry.json` still pointed `web-fetch` at the deleted
  `layer-tools/mcp-tools/web-fetch` path instead of the repo template path under
  `services/mcp-tools/web-fetch`.

## Intended repair
- Restore the ignored upstream SearXNG checkout under `services/searxng/app`.
- Rebuild the local SearXNG virtualenv with the tracked bootstrap script.
- Replace the live Mini systemd unit from the repo-managed template.
- Re-sync the runtime MCP registry to the tracked template.
- Verify the full Mini client chain: direct SearXNG, LiteLLM `/v1/search`,
  MCP `search.web`, and Open WebUI web search.

## Runtime notes
- Host: Mini
- Scope: SearXNG runtime repair plus Mini-local consumer revalidation only
- Explicit non-goals: no `websearch-orch`, no Studio/OptiLLM mutation, no bind
  or exposure changes

## Outcome
- Restored the ignored SearXNG checkout and virtualenv under the canonical host
  path `/home/christopherbailey/homelab-llm/services/searxng/app`.
- Replaced the live Mini systemd unit from
  `platform/ops/systemd/searxng.service`.
- Synced `/etc/homelab-llm/mcp-registry.json` to
  `platform/ops/templates/mcp-registry.json`.
- Confirmed the supported Mini chain is functional again:
  - `systemctl is-active searxng.service` => `active`
  - `ss -ltnp | rg ':8888\\b'` => listener on `127.0.0.1:8888`
  - `curl -fsS "http://127.0.0.1:8888/search?q=homelab&format=json"` returned
    `19` results
  - authenticated LiteLLM `POST /v1/search/searxng-search` returned `200`
  - MCP `search.web` via `uv run --directory ... python scripts/demo_client.py`
    returned normalized OpenVINO search results
  - Open WebUI `POST /api/chat/completions` with `features.web_search=true`
    returned assistant content plus a `sources` payload

## Root cause detail
- The repo-managed systemd template had already moved SearXNG to
  `services/searxng/app`, but the live host unit still pointed at the deleted
  `layer-tools/searxng/app` path.
- The first repair attempt restored the app only inside the linked worktree,
  which kept the host runtime broken because systemd resolves the primary repo
  path. The durable fix was restoring the ignored checkout at the primary path.

## Residual notes
- SearXNG starts cleanly enough for the supported path, but startup logs still
  show non-fatal engine init noise for `ahmia`, `torch`, and `wikidata`.
- LiteLLM logs still emit the existing non-fatal search-path warning:
  `cannot override response model; missing model attribute` for
  `SearchResponse`.
