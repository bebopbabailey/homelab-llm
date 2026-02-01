# INTEGRATIONS

## LiteLLM routing
- Config: `layer-gateway/litellm-orch/config/router.yaml` + `layer-gateway/litellm-orch/config/env.local`.
- Router settings: retries and cooldowns in `layer-gateway/litellm-orch/config/router.yaml`.
- Upstreams: MLX `http://192.168.1.72:<port>/v1`,
  AFM (planned) `http://192.168.1.72:9999/v1`.
- Model naming: canonical model IDs with prefix `mlx-`.
  Format: `mlx-<family>-<params>-<quant>-<variant>` in that order (dash-only,
  no vendor/org prefixes). Handles must match the canonical model ID.
  OptiLLM techniques are selected per-request via `optillm_approach` rather than
  exploding model handles.
- For OpenAI-compatible upstreams, keep model aliases as handles and set the backend `litellm_params.model` to `openai/<base-model>`.
- Logs: JSON logs enabled (`litellm_settings.json_logs: true`).
- OptiLLM request fields are passed through by setting `litellm_settings.drop_params: false`
  (only relevant when calling OptiLLM directly).
- Auth: proxy key planned via `LITELLM_PROXY_KEY`.
- Health timeout: `HEALTH_CHECK_TIMEOUT_SECONDS` (env) controls `/health` probe timeout (set to 5s).
- MLX alias set (fixed ports): `mlx-*` (ports `8100-8119` team); `8120-8139` reserved for experimental tests.
- MLX registry is the canonical link from `model_id` to inference source:
  `model_id` → `registry.json` → `source_path` / `cache_path`.
- Context defaults: `router.yaml` uses MLX registry fields:
  `context_length` → `max_input_tokens`, `max_output_tokens` (currently 65k).
  These defaults are persisted in the Studio registry and synced via `mlxctl sync-gateway`.
- **Showroom vs backroom:** only models present on the Mini or Studio are exposed
  as LiteLLM handles. Seagate storage is **backroom only** and never receives handles.
- Health policy: use `/health/readiness` as the default health signal. `/health` is
  a deep probe that can report unhealthy when backends are intentionally offline.
- Aliases: `main`, `deep`, `fast`, `swap` are the stable LiteLLM handles.
- Experiments: `x1`–`x4` are reserved for experimental routing.

### Param support probe (LiteLLM + MLX backends)
Run this on the **Mini** to verify which optional params are accepted or ignored:
```bash
curl -sS --max-time 10 http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-gpt-oss-20b-mxfp4-q4",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 256,
    "temperature": 0.2,
    "top_p": 0.9,
    "presence_penalty": 0.4,
    "frequency_penalty": 0.2
  }'
```
Expected: either a normal response (params accepted/ignored) or a 4xx validation error
if a param is rejected by the backend.

**Probe note (Jan 19, 2026):** running the above from this repo shell timed out
(`http://127.0.0.1:4000/health` did not respond). Re-run on the Mini host.

## Open WebUI -> LiteLLM
- Env: `/etc/open-webui/env` uses `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`.
- Health: `/health` on port 3000.
 - Web search (via LiteLLM): `/v1/search/searxng-search`.

## SearXNG search
- Local SearXNG: `http://127.0.0.1:8888/search?q=<query>&format=json`
- LiteLLM proxy: `http://127.0.0.1:4000/v1/search/searxng-search`
- Env: `SEARXNG_API_BASE=http://127.0.0.1:8888`
- Tool name: `searxng-search`
- OptiLLM `web_search` plugin also uses SearXNG when `SEARXNG_API_BASE` is set in `/etc/optillm-proxy/env`.

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

## OpenCode (client)
- Config: `~/.config/opencode/opencode.json` (MacBook).
- Provider: LiteLLM OpenAI-compatible `baseURL=http://100.69.99.60:4000/v1`.
- Models: use LiteLLM handles (e.g., `main`, `deep`, `fast`, `swap`).
- Permissions: set `bash`/`edit` to `ask` for explicit approval before shell/network.
- Web search uses MCP `web-fetch` (stdio) with `search.web` routed to
  LiteLLM `/v1/search/searxng-search`.

## OptiLLM boost lane (opt-in)
- `boost`: OptiLLM router decides whether to apply an approach (including “none”) using the main base model.
- `boost-deep`: same, but uses the deep base model.
- Force a specific approach by sending `optillm_approach` in the request body (e.g., `bon`, `moa`, `plansearch`).
- Observability: OptiLLM logs the selected approach at INFO level (`Using approach(es) [...]`) in `optillm-proxy` logs. No response header is currently documented for approach selection.
 - OptiLLM proxy default approach is `router` (systemd flag); requests without `optillm_approach` use router.
 - OptiLLM proxy requires `Authorization: Bearer <OPTILLM_API_KEY>` even on localhost; missing headers return an “Invalid Authorization header” error.

### OptiLLM validation checklist (router + plugins)
1) Router is active (log line: `Using approach(es) ['router']`).
2) `web_search` returns results **without** Chrome errors (SearXNG path).
3) `deep_research` uses the same SearXNG path (no Selenium dependency).
4) `boost` and `boost-deep` return 200 with non-empty `message.content`.

## LiteLLM extension points (summary)
See `layer-gateway/litellm-orch/docs/litellm-extension-points.md` for the hook map
and where this repo uses callbacks vs guardrails.

## OpenVINO backend (not wired in LiteLLM)
- Systemd unit: `/etc/systemd/system/ov-server.service` (binds `0.0.0.0` for maintenance).
- Env: `/etc/homelab-llm/ov-server.env` (runtime).
- Endpoints: `/health`, `/v1/models`, `/v1/chat/completions`.
- Ops: `/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl` controls model warm-up profiles.
- Status: available as a standalone backend; no LiteLLM handles are currently registered.

## OptiLLM optimization proxy
- Local-only proxy: `http://127.0.0.1:4020/v1`.
- **Current (ergonomic) usage:** call OptiLLM directly and set `optillm_approach`
  as a top-level JSON field. This works from Open WebUI (custom params), curl,
  iOS Shortcuts, and any OpenAI-compatible client.
- Requests must include `Authorization: Bearer <OPTILLM_API_KEY>` (even for localhost tests).
- **Deprecated:** routing all MLX handles through OptiLLM and maintaining
  `router-mlx-*` loop-avoidance entries in LiteLLM.
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

### Technique selection (request body)
Set `optillm_approach` in the request body:
- `moa`: Mixture-of-Agents (strong reasoning, higher latency)
- `bon`: best-of-n sampling (faster than MoA, moderate gains)
- `plansearch`: planning/search (slower, good for multi-step tasks)
- `self_consistency`: consistency voting (slower, robust)

Example:
```json
{"model":"mlx-gpt-oss-120b-mxfp4-q4","messages":[{"role":"user","content":"ping"}],"optillm_approach":"moa"}
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
