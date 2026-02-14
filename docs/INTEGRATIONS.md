# INTEGRATIONS

## LiteLLM routing
- Config: `layer-gateway/litellm-orch/config/router.yaml` + `layer-gateway/litellm-orch/config/env.local`.
- Router settings: retries and cooldowns in `layer-gateway/litellm-orch/config/router.yaml`.
- Upstreams: MLX Omni (canonical) `http://192.168.1.72:8100/v1`,
  AFM (planned) `http://192.168.1.72:9999/v1`.
- Model naming: canonical model IDs with prefix `mlx-`.
  Format: `mlx-<family>-<params>-<quant>-<variant>` in that order (dash-only,
  no vendor/org prefixes). Handles must match the canonical model ID.
  OptiLLM techniques are selected per-request via `optillm_approach` rather than
  exploding model handles.
- For OpenAI-compatible upstreams, keep model aliases as handles and set the backend `litellm_params.model` to `openai/<base-model>`.
- Logs: JSON logs are currently disabled (`litellm_settings.json_logs: false`).
- OptiLLM request fields are passed through by setting `litellm_settings.drop_params: false`
  (only relevant when calling OptiLLM directly).
- Auth: gateway requests currently require bearer auth (`LITELLM_MASTER_KEY` in deployment).
- Health timeout: `HEALTH_CHECK_TIMEOUT_SECONDS` (env) controls `/health` probe timeout (set to 5s).
- MLX alias set (canonical endpoint): `mlx-*` routes to Omni `:8100` and selects the model via the request `model` field.
  `8120-8139` remain reserved for experimental canaries (only used when explicitly configured).
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
- LiteLLM `/v1/models` is **alias-only** (canonical `mlx-*` IDs are omitted from the list).

### LiteLLM Prometheus metrics (enabled)
- `/metrics/` endpoint is exposed by the LiteLLM proxy on the same port (4000).
- **Auth is required** (same bearer auth as `/v1/*` endpoints).
- Hitting `/metrics` (no trailing slash) returns **307** → use `/metrics/`.
- Enable via `litellm_settings.callbacks: ["prometheus"]` in `router.yaml`.
- Metric names vary by version; verify in `/metrics/` before building dashboards.

PromQL examples (Grafana):
```promql
# Requests per second (proxy)
sum(rate(litellm_proxy_total_requests_metric_total[1m]))

# End-to-end request p95 latency (seconds)
histogram_quantile(0.95, sum(rate(litellm_request_total_latency_metric_bucket[5m])) by (le, model))

# Time-to-first-token (TTFT) p95 (seconds)
histogram_quantile(0.95, sum(rate(litellm_llm_api_time_to_first_token_metric_bucket[5m])) by (le, model))

# Error rate (proxy)
sum(rate(litellm_proxy_failed_requests_metric_total[1m])) 
  / sum(rate(litellm_proxy_total_requests_metric_total[1m]))

# Tokens per second (total)
sum(rate(litellm_total_tokens_metric_total[1m]))

# Tokens per second (input/output)
sum(rate(litellm_input_tokens_metric_total[1m]))
sum(rate(litellm_output_tokens_metric_total[1m]))
```
- Common metric families observed (verify via `/metrics/`):
  - `litellm_proxy_total_requests_metric_total`
  - `litellm_proxy_failed_requests_metric_total`
  - `litellm_request_total_latency_metric_*` (histogram)
  - `litellm_llm_api_time_to_first_token_metric_*` (histogram)
  - `litellm_total_tokens_metric_total`, `litellm_input_tokens_metric_total`, `litellm_output_tokens_metric_total`
  - `litellm_deployment_latency_per_output_token_*` (histogram)

### Prometheus + Grafana (Mini)
- Prometheus: `http://127.0.0.1:9090` (localhost only).
- Grafana: `http://127.0.0.1:3001` (localhost only).
- Grafana datasource is provisioned to Prometheus on startup.
- Dashboards live in `layer-interface/grafana/dashboards/` (deployed copy under `/etc/homelab-llm/grafana/dashboards/`).
- Prometheus runtime config: `/etc/homelab-llm/prometheus/prometheus.yml` (deployed from repo).
- Experimental aliases (`x1`–`x4`) are not currently configured in active router config.

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

## Tailscale Services (tailnet HTTPS)
- Services are exposed via `tailscale serve --service=svc:<name>` on the Mini.
- Hostnames (tailnet only):
  - `https://code.tailfd1400.ts.net/` → code-server (8080)
  - `https://chat.tailfd1400.ts.net/` → Open WebUI (3000)
  - `https://gateway.tailfd1400.ts.net/` → LiteLLM (4000)
  - `https://search.tailfd1400.ts.net/` → SearXNG (8888)
- Access is controlled by **grants** (not legacy ACLs). Use `svc:*` in `dst`.

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
- `boost` routes to the Studio OptiLLM proxy (`http://192.168.1.72:4020/v1`) via `OPTILLM_API_BASE`.
- Force a specific approach by sending `optillm_approach` in the request body (e.g., `bon`, `moa`, `plansearch`).
- Observability: `boost` appears in Studio `optillm-proxy` logs.
- Requests must include bearer auth for the target backend key (`OPTILLM_API_KEY` for `boost`).

### OptiLLM validation checklist (router + plugins)
1) Router is active (log line: `Using approach(es) ['router']`).
2) `web_search` returns results **without** Chrome errors (SearXNG path).
3) `deep_research` uses the same SearXNG path (no Selenium dependency).
4) `boost` returns 200 with non-empty `message.content`.

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
- Studio-local proxy: `http://192.168.1.72:4020/v1` (binds `0.0.0.0:4020` on the Studio).
- Current usage: active LiteLLM `boost` path.
- Requests must include `Authorization: Bearer <OPTILLM_API_KEY>` (even for localhost tests).
- Upstream can be LiteLLM or MLX directly; avoid routing loops.
- Proxy providers config: `~/.optillm/proxy_config.yaml` must point only to
  LiteLLM to avoid cloud fallbacks.

### Boost handle routing (current)
- LiteLLM `boost` routes to Studio OptiLLM proxy via `OPTILLM_API_BASE`.
- This keeps clients LiteLLM-only while still allowing request-body technique
  selection (e.g., `optillm_approach`).

### Technique selection (request body)
Set `optillm_approach` in the request body:
- `moa`: Mixture-of-Agents (strong reasoning, higher latency)
- `bon`: best-of-n sampling (faster than MoA, moderate gains)
- `plansearch`: planning/search (slower, good for multi-step tasks)
- `self_consistency`: consistency voting (slower, robust)
Local-only (best on opti-local due to multi-sample or decoding-level control):
  - `bon`, `moa`, `mcts`, `pvg`, `cot_decoding`, `entropy_decoding`,
  `deepconf`, `thinkdeeper`, `autothink`

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
- Prefer tailnet HTTPS: `https://gateway.tailfd1400.ts.net/v1`.
- Local host-only calls use `http://127.0.0.1:4000/v1` (on the Mini).
