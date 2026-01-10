# INTEGRATIONS

## LiteLLM routing
- Config: `config/router.yaml` + `config/env.local`.
- Router settings: retries and cooldowns in `config/router.yaml`.
- Upstreams: MLX `http://192.168.1.72:<port>/v1`, OpenVINO `http://localhost:9000/v1`.
- Model naming: `jerry-{xl,l,m,s}`, `bench-{xl,l,m,s}`, `utility-{a,b}`, `benny-*`.
  Upstream model IDs use `openai/<upstream>`.
- Logs: JSON logs enabled (`litellm_settings.json_logs: true`).
- Auth: proxy key planned via `LITELLM_PROXY_KEY`.
 - MLX alias set (fixed ports): `jerry-xl/l/m/s`, `bench-xl/l/m/s`, `utility-a/b`.

## Open WebUI -> LiteLLM
- Env: `/etc/open-webui/env` uses `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`.
- Health: `/health` on port 3000.
 - Web search (via LiteLLM): `/v1/search/searxng-search` once configured.

## SearXNG search
- Local SearXNG: `http://127.0.0.1:8888/search?q=<query>&format=json`
- LiteLLM proxy: `http://127.0.0.1:4000/v1/search/searxng-search`
- Env: `SEARXNG_API_BASE=http://127.0.0.1:8888`
- Tool name: `searxng-search`

## Web fetch + clean (planned)
- Purpose: fetch a URL and return clean, model-ready text for summarization,
  RAG, or schema extraction.
- Implemented as MCP stdio tool (`services/web-fetch`) exposing `web.fetch`
  and `search.web` (LiteLLM `/v1/search` backend).
- Recommended `web.fetch` stack: `httpx` + `trafilatura` (primary extraction)
  + `readability-lxml` (fallback) + `selectolax`/`lxml` (cleanup).
- Schematron note: it ignores prompts and uses only schema + input. Provide
  trimmed HTML or clean text for best extraction.

## OpenVINO backend
- User systemd unit: `/home/christopherbailey/.config/systemd/user/ov-server.service`.
- Endpoints: `/health`, `/v1/models`, `/v1/chat/completions`.
- LiteLLM routes `benny-*` via `BENNY_*_API_BASE` and `BENNY_*_MODEL`.
- Alias map (shared backends for lean footprint):
  - `benny-route-m` → `benny-tool-s`
  - `benny-tool-m` → `benny-classify-m`
  - `benny-extract-s` → `benny-clean-s`
  - `benny-extract-m` → `benny-summarize-m`

## OptiLLM optimization proxy
- Local-only proxy: `http://127.0.0.1:4020/v1`.
- LiteLLM route: `plan-architect` → OptiLLM (`OPTILLM_PLAN_API_BASE`, `OPTILLM_PLAN_MODEL`, `OPTILLM_PLAN_API_KEY`).
- Loop-avoidance: LiteLLM sends prefixed model names (e.g., `moa-jerry-architect`); OptiLLM strips prefix upstream.
- Auth: LiteLLM must send `Authorization: Bearer <OPTILLM_API_KEY>`.

## Tiny Agents hook (plan)
- Add `TINYAGENTS_API_BASE` and `TINYAGENTS_MODEL` to env.
- Add a `model_list` entry in `config/router.yaml`.
- Update `PLATFORM_DOSSIER.md` before new LAN exposure.

## MCP tools (planned)
- MCP servers provide tool access; TinyAgents is the MCP client.
- Keep tool calls separate from LiteLLM model calls.
- Plan a sandboxed `python.run` tool for future workflows; avoid unsandboxed
  execution by default.

## Client base URL recommendation
- Prefer `http://mini:4000` only if name resolution is configured.
- Fallback: `http://192.168.1.71:4000`.
