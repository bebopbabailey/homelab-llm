# INTEGRATIONS

## LiteLLM routing
- Config: `services/litellm-orch/config/router.yaml` + `services/litellm-orch/config/env.local`.
- Router settings: retries and cooldowns in `services/litellm-orch/config/router.yaml`.
- Upstreams: MLX `http://192.168.1.72:<port>/v1`, OpenVINO `http://localhost:9000/v1`,
  AFM (planned) `http://192.168.1.72:9999/v1`.
- Model naming: `jerry-{xl,l,m,s}`, `bench-{xl,l,m,s}`, `utility-{a,b}`, `benny-*`.
  Upstream model IDs use `openai/<upstream>`.
- Logs: JSON logs enabled (`litellm_settings.json_logs: true`).
- Auth: proxy key planned via `LITELLM_PROXY_KEY`.
 - MLX alias set (fixed ports): `jerry-xl/l/m/s`, `bench-xl/l/m/s`, `utility-a/b`.

## Open WebUI -> LiteLLM
- Env: `/etc/open-webui/env` uses `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`.
- Health: `/health` on port 3000.
 - Web search (via LiteLLM): `/v1/search/searxng-search`.

## SearXNG search
- Local SearXNG: `http://127.0.0.1:8888/search?q=<query>&format=json`
- LiteLLM proxy: `http://127.0.0.1:4000/v1/search/searxng-search`
- Env: `SEARXNG_API_BASE=http://127.0.0.1:8888`
- Tool name: `searxng-search`

## Web fetch + clean (implemented, MCP stdio)
- Purpose: fetch a URL and return clean, model-ready text for summarization,
  RAG, or schema extraction.
- Implemented as MCP stdio tool (`services/web-fetch`) exposing `web.fetch`
  and `search.web` (LiteLLM `/v1/search` backend). Invoked by an MCP client;
  not running as a systemd service yet.
- Recommended `web.fetch` stack: `httpx` + `trafilatura` (primary extraction)
  + `readability-lxml` (fallback) + `selectolax`/`lxml` (cleanup).
- Schematron note: it ignores prompts and uses only schema + input. Provide
  trimmed HTML or clean text for best extraction.

## OpenVINO backend
- Systemd unit: `/etc/systemd/system/ov-server.service` (binds `0.0.0.0` for maintenance).
- Env: `/etc/homelab-llm/ov-server.env` (runtime).
- Endpoints: `/health`, `/v1/models`, `/v1/chat/completions`.
- Ops: `/home/christopherbailey/homelab-llm/ops/scripts/ovctl` controls model warm-up profiles.
- LiteLLM routes `benny-*` via `BENNY_*_API_BASE` and `BENNY_*_MODEL`.
  Current defaults use int8 for `benny-clean-s` and `benny-clean-m` via
  `benny-clean-*-int8` model IDs in `services/litellm-orch/config/env.local`.
  int4 exists in the registry but is GPU-unstable on this iGPU stack.
  Runtime device is currently `OV_DEVICE=GPU` (see `/etc/homelab-llm/ov-server.env`);
  evaluating `AUTO` and `MULTI:GPU,CPU` for multi-request throughput.
  Pending: evaluate int8 for `benny-extract-*`, `benny-summarize-*`, `benny-tool-*`
  and decide whether to switch their routing defaults.
- Alias map (shared backends for lean footprint):
  - `benny-route-m` → `benny-tool-s`
  - `benny-tool-m` → `benny-classify-m`
  - `benny-extract-s` → `benny-clean-s` (fp16 registry entry)
  - `benny-extract-m` → `benny-summarize-m`

## OptiLLM optimization proxy
- Local-only proxy: `http://127.0.0.1:4020/v1`.
- LiteLLM routes:
  - `optillm-jerry-xl` → OptiLLM (`OPTILLM_JERRY_XL_API_BASE`, `OPTILLM_JERRY_XL_MODEL=openai/moa-jerry-xl`, `OPTILLM_JERRY_XL_API_KEY`)
  - `optillm-jerry-l` → OptiLLM (`OPTILLM_JERRY_L_API_BASE`, `OPTILLM_JERRY_L_MODEL=openai/moa-jerry-l`, `OPTILLM_JERRY_L_API_KEY`)
- Loop-avoidance: LiteLLM sends prefixed model names (e.g., `moa-jerry-xl`); OptiLLM strips prefix upstream.
- Auth: LiteLLM must send `Authorization: Bearer <OPTILLM_API_KEY>` (configured
  via `--optillm-api-key`, not env, to avoid local inference mode).
- OptiLLM runs with `--approach proxy` to allow per-request technique selection
  via model name prefixes.
- Proxy providers config: `~/.optillm/proxy_config.yaml` must point only to
  LiteLLM to avoid cloud fallbacks.

### Technique selection (model prefixes)
Change the model prefix in LiteLLM env to pick techniques:
- `moa-<base>`: Mixture-of-Agents (strong reasoning, higher latency)
- `bon-<base>`: best-of-n sampling (faster than MoA, moderate gains)
- `plansearch-<base>`: planning/search (slower, good for multi-step tasks)
- `self_consistency-<base>`: consistency voting (slower, robust)

Example:
```
OPTILLM_JERRY_XL_MODEL=openai/bon-jerry-xl
```

## Tiny Agents hook (plan)
- Add `TINYAGENTS_API_BASE` and `TINYAGENTS_MODEL` to env.
- Add a `model_list` entry in `config/router.yaml`.
- Update `PLATFORM_DOSSIER.md` before new LAN exposure.

## AFM backend (planned, Studio)
- AFM runs an OpenAI-compatible API on the Studio (target: `http://192.168.1.72:9999/v1`).
- Wire AFM as a LiteLLM backend once:
  - base URL is confirmed,
  - model ID(s) are known from `GET /v1/models`,
  - auth requirements (if any) are defined.

## MCP tools (implemented locally)
- MCP servers provide tool access; TinyAgents is the MCP client (MVP).
- MCP registry lives at `/etc/homelab-llm/mcp-registry.json` (pending creation).
- Template: `ops/templates/mcp-registry.json`.
- Keep tool calls separate from LiteLLM model calls.
- Plan a sandboxed `python.run` tool for future workflows; avoid unsandboxed
  execution by default.

## Client base URL recommendation
- Prefer `http://mini:4000` only if name resolution is configured.
- Fallback: `http://192.168.1.71:4000`.
