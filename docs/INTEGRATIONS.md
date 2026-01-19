# INTEGRATIONS

## LiteLLM routing
- Config: `layer-gateway/litellm-orch/config/router.yaml` + `layer-gateway/litellm-orch/config/env.local`.
- Router settings: retries and cooldowns in `layer-gateway/litellm-orch/config/router.yaml`.
- Upstreams: MLX `http://192.168.1.72:<port>/v1`, OpenVINO `http://localhost:9000/v1`,
  AFM (planned) `http://192.168.1.72:9999/v1`.
- Model naming: canonical model IDs with prefixes `mlx-*`, `ov-*`, `opt-*`.
  Handles for models must match the canonical model ID (dash-only, no vendor prefixes).
  Exception: OptiLLM uses technique prefixes (e.g., `moa-`, `bon-`) in the
  **selector** sent to OptiLLM; handles stay `opt-*`.
- For OpenAI-compatible upstreams, keep model aliases as handles and set the backend `litellm_params.model` to `openai/<base-model>`.
- Logs: JSON logs enabled (`litellm_settings.json_logs: true`).
- Auth: proxy key planned via `LITELLM_PROXY_KEY`.
- MLX alias set (fixed ports): `mlx-*` (ports `8100-8119` team); `8120-8139` reserved for experimental tests.
- MLX registry is the canonical link from `model_id` to inference source:
  `model_id` → `registry.json` → `source_path` / `cache_path`.
- Context defaults: `router.yaml` uses MLX registry fields:
  `context_length` → `max_input_tokens`, `max_output_tokens` (currently 65k).
  These defaults are persisted in the Studio registry and synced via `mlxctl sync-gateway`.
- **Showroom vs backroom:** only models present on the Mini or Studio are exposed
  as LiteLLM handles. Seagate storage is **backroom only** and never receives handles.

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
- Implemented as MCP stdio tool (`layer-tools/mcp-tools/web-fetch`) exposing `web.fetch`
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
- Ops: `/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl` controls model warm-up profiles.
- LiteLLM routes `ov-*` via `OV_*_API_BASE` and `OV_*_MODEL`.
  Current aliases map directly to base OpenVINO model IDs:
  `ov-qwen2-5-3b-instruct-fp16`, `ov-qwen2-5-1-5b-instruct-fp16`, `ov-phi-4-mini-instruct-fp16`,
  `ov-phi-3-5-mini-instruct-fp16`, `ov-llama-3-2-3b-instruct-fp16`, `ov-mistral-7b-instruct-v0-3-fp16`.
  Runtime device is currently `OV_DEVICE=GPU` (see `/etc/homelab-llm/ov-server.env`);
  evaluating `AUTO` and `MULTI:GPU,CPU` for multi-request throughput.
  The previous `ov-*` role aliases are deprecated.

## OptiLLM optimization proxy
- Local-only proxy: `http://127.0.0.1:4020/v1`.
- LiteLLM routes OptiLLM selectors via `OPTILLM_<HANDLE>_*` env vars.
- Current OptiLLM handles: _none (direct routing via MLX handles)_.
- Loop-avoidance: LiteLLM sends prefixed model names (e.g., `router-<base-model>`);
  OptiLLM strips the prefix upstream.
- Current wiring: **all MLX handles route to OptiLLM**, and OptiLLM calls LiteLLM with
  `router-mlx-*` model names that are mapped directly to MLX ports.
  These `router-mlx-*` entries are internal (not in `handles.jsonl`) but will appear
  in LiteLLM `/v1/models`.
- Toggle: `mlxctl sync-gateway --no-route-via-optillm` disables this mode.
  Default is enabled via `MLX_ROUTE_VIA_OPTILLM=1`.
- Auth: LiteLLM must send `Authorization: Bearer <OPTILLM_API_KEY>` (configured
  via `--optillm-api-key`, not env, to avoid local inference mode).
- OptiLLM runs with `--approach proxy` to allow per-request technique selection
  via model name prefixes.
- Proxy providers config: `~/.optillm/proxy_config.yaml` must point only to
  LiteLLM to avoid cloud fallbacks.

## OptiLLM local inference (Studio)
- Separate local inference instances (PyTorch/MPS) run on the Studio:
  - `4040` → `opt-router-high`
  - `4041` → `opt-router-balanced`
  - `4042` → `opt-router-fast`
- These are distinct from the Mini proxy and use single-model local inference.
- Local instances are currently disabled by default until setup is finalized.
- Standard HF cache on Studio: `/Users/thestudio/models/hf/hub`.
- Pin `transformers<5` for router compatibility.

### Technique selection (model prefixes)
Change the model prefix in LiteLLM env to pick techniques:
- `moa-<base>`: Mixture-of-Agents (strong reasoning, higher latency)
- `bon-<base>`: best-of-n sampling (faster than MoA, moderate gains)
- `plansearch-<base>`: planning/search (slower, good for multi-step tasks)
- `self_consistency-<base>`: consistency voting (slower, robust)

Example:
```
OPTILLM_OPT_ROUTER_EXAMPLE_MODEL=openai/router-<base-model>
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
- Template: `platform/ops/templates/mcp-registry.json`.
- Keep tool calls separate from LiteLLM model calls.
- Plan a sandboxed `python.run` tool for future workflows; avoid unsandboxed
  execution by default.

## Client base URL recommendation
- Prefer `http://mini:4000` only if name resolution is configured.
- Fallback: `http://192.168.1.71:4000`.
