# INTEGRATIONS

## LiteLLM routing
- Config: `services/litellm-orch/config/router.yaml` + `services/litellm-orch/config/env.local`.
- Router settings: retries and cooldowns in `services/litellm-orch/config/router.yaml`.
- Upstreams: active Studio MLX lane `http://192.168.1.72:8101/v1`,
  active `llmster` GPT service on `8126`,
  AFM (planned) `http://192.168.1.72:9999/v1`.
- Model naming: canonical model IDs with prefix `mlx-`.
  Format: `mlx-<family>-<params>-<quant>-<variant>` in that order (dash-only,
  no vendor/org prefixes). Handles must match the canonical model ID.
  OptiLLM techniques are selected per-request via `optillm_approach` rather than
  exploding model handles.
- For OpenAI-compatible upstreams, keep model aliases as handles and set the backend `litellm_params.model` to `openai/<base-model>`.
- Logs: JSON logs are currently disabled (`litellm_settings.json_logs: false`).
- Unsupported OpenAI params are dropped at LiteLLM via `litellm_settings.drop_params: true`.
- Auth: gateway requests currently require bearer auth (`LITELLM_MASTER_KEY` in deployment).
- Health timeout: `HEALTH_CHECK_TIMEOUT_SECONDS` (env) controls `/health` probe timeout (set to 5s).
- Current live lane mapping:
  - `deep` -> `8126` (`llmster-gpt-oss-120b-mxfp4-gguf`)
  - `main` -> `8101` (`mlx-qwen3-next-80b-mxfp4-a3b-instruct`)
  - `fast` -> `8126` (`llmster-gpt-oss-20b-mxfp4-gguf`)
  `8120-8139` remain approved experimental/canary space, with `8126` now
  active for the shared canonical GPT service carrying `fast` and `deep`.
- Studio service posture:
  - `8126` is the active shared GPT-family service lane for public `fast` and `deep`
  - `8123-8125` are retired shadow ports and are not part of the current control surface
- Canonical GPT backend identity on `8126` is MXFP4 GGUF:
  - `llmster-gpt-oss-20b-mxfp4-gguf`
  - `llmster-gpt-oss-120b-mxfp4-gguf`
- Raw llama.cpp truth-path mirrors for GPT rollout are loopback-only on Studio:
  - `fast` mirror -> `127.0.0.1:8130`
  - `deep` mirror -> `127.0.0.1:8131` (planned)
  They are not part of the public client path and are diagnostic-first rather
  than automatic promotion oracles.
- MLX registry is the canonical link from `model_id` to inference source:
  `model_id` → `registry.json` → `source_path` / `cache_path`.
- Context defaults: `router.yaml` uses MLX registry fields:
  `context_length` → `max_input_tokens`, `max_output_tokens` (currently 65k).
  These defaults are persisted in the Studio registry and synced via `mlxctl sync-gateway`.
- **Showroom vs backroom:** only models present on the Mini or Studio are exposed
  as LiteLLM handles. Seagate storage is **backroom only** and never receives handles.
- Studio GPT retention policy is “active runtime artifacts plus one staged next
  artifact”; stale model weights should be pruned before GPT cutovers.
- Health policy: use `/health/readiness` as the default health signal. `/health` is
  a deep probe that can report unhealthy when backends are intentionally offline.
- Stable local public LLM aliases: `main`, `deep`, `fast`.
- Additive experimental Codex-backed alias: `chatgpt-5`.
- There are no active temporary GPT rollout aliases in the current gateway
  contract.
- `main` is closed as an active backend project and remains accepted for public
  use with known limitations on forced-tool semantics and structured outputs.
- Resilience baseline: `fast -> main`.
- GPT human-chat lanes are Chat Completions-first in the current Open WebUI
  contract.
- `main`, `deep`, `fast`, and `chatgpt-5` are all accepted on
  `POST /v1/chat/completions`.
- `/v1/responses` remains available for direct callers on compatible lanes.
- `deep` cutover evidence was:
  - close `fast` observation on the current live LM Studio stack
  - refresh raw standalone llama.cpp while live `llmster` remained untouched
  - refresh LM Studio daemon/runtime
  - rerun the `fast` regression gate
  - stage/import `deep`, prove shared posture, validate the temporary canary,
    and repoint canonical public `deep`
- Current public `deep` result on shared `8126`:
  - plain chat clean
  - structured simple clean
  - structured nested clean
  - auto noop `10/10`
  - auto arg-bearing `10/10`
  - `required` arg-bearing `9/10`
  - named forced-tool choice unsupported on the current backend path
- Experimental aliases remain opt-in and additive. They do not replace the
  stable local alias contract and are not used as automatic fallback targets.
- LiteLLM `/v1/models` is **alias-only** (canonical `mlx-*` IDs are omitted from the list).

### LiteLLM Prometheus metrics (enabled)
- `/metrics/` endpoint is exposed by the LiteLLM proxy on the same port (4000).
- Endpoint is currently reachable without bearer auth in this deployment.
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
- Dashboards live in `services/grafana/dashboards/` (deployed copy under `/etc/homelab-llm/grafana/dashboards/`).
- Prometheus runtime config: `/etc/homelab-llm/prometheus/prometheus.yml` (deployed from repo).
- Experimental aliases (`x1`–`x4`) are not currently configured in active router config.

### Param support probe (LiteLLM + canonical backends)
Run this on the **Mini** to verify which optional params are accepted or ignored:
```bash
curl -sS --max-time 10 http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "fast",
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
- Open WebUI continues to talk only to LiteLLM; no upstream provider rewrite is
  required for ChatGPT-backed aliases.
- Health: `/health` on port 3000.
- Canonical voice path uses dedicated Open WebUI `AUDIO_STT_*` and `AUDIO_TTS_*`
  settings pointed at LiteLLM, not direct Orin URLs.
- LiteLLM speech aliases:
  - canary: `voice-stt-canary`, `voice-tts-canary`
  - stable: `voice-stt`, `voice-tts`
- LiteLLM transcript-cleanup aliases:
  - standard: `task-transcribe`
  - vivid: `task-transcribe-vivid`
- LiteLLM experimental Codex-backed alias:
  - `chatgpt-5`
- `task-transcribe*` is a `POST /v1/chat/completions` text-cleanup contract only.
  It is not part of the Open WebUI `AUDIO_STT_*` speech path.
- LiteLLM transcript-to-JSON utility alias:
  - `task-json`
- `task-json` is also a `POST /v1/chat/completions` utility contract only.
  It returns canonical JSON extraction output and is not part of the Open WebUI
  `AUDIO_STT_*` speech path.
- `chatgpt-5` is now backed by Mini-local experimental `ccproxy-api` on
  `127.0.0.1:4010/codex/v1`, with LiteLLM still serving as the only user-facing
  gateway.
- Open WebUI uses the standard OpenAI-compatible Chat Completions path again
  against LiteLLM, which avoids the previous empty-output failure on the raw
  ChatGPT backend path.
- The current validated upstream model id for the alias is `gpt-5.3-codex`.
- LiteLLM routes the speech aliases directly to the Orin `voice-gateway` LAN `/v1`
  facade. `voice-gateway` then forwards to localhost-only Speaches.
- Web search (active path): `WEB_SEARCH_ENGINE=searxng` with `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`.
- Result and loader policy is explicit in documented Open WebUI env vars:
  `WEB_SEARCH_RESULT_COUNT=6`, `WEB_SEARCH_CONCURRENT_REQUESTS=1`,
  `WEB_LOADER_ENGINE=safe_web`, `WEB_LOADER_TIMEOUT=15`,
  `WEB_LOADER_CONCURRENT_REQUESTS=2`,
  `WEB_FETCH_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`,
  `WEB_SEARCH_DOMAIN_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`.
- LiteLLM `/v1/search/searxng-search` remains available for direct callers and MCP tools.
- Open WebUI audio settings for this path still come from systemd env/drop-ins,
  but the deployment currently uses persistent config for other settings such as
  terminal/tool server registrations.
- Speech canary promotion requires a post-restart verification that the effective
  `AUDIO_*` settings still match the env values and are not being overridden by stale
  Admin UI state.

## Web Search Ownership Boundary
- Open WebUI owns web-search UX plus provider/loader configuration.
- LiteLLM owns routing/auth/retries/fallbacks and generic `/v1/search/<tool_name>` access only.
- vLLM owns inference and explicit structured decoding only when the caller requests it.
- Pushcut is not active in the current LiteLLM main runtime.
- No custom web-search business logic lives in LiteLLM guardrails.
- No custom business logic is coupled to Open WebUI prompt internals.
- Any future external search/loader service must use documented Open WebUI external
  endpoints with a clean service boundary.
- Migration note: the old custom path was intentionally removed. There is no active
  `websearch-orch` middle service, no legacy source-tag coupling, and no LiteLLM
  schema injection/repair/render loop for web search.

## Tailscale Services (tailnet HTTPS)
- Services are exposed via `tailscale serve --service=svc:<name>` on the Mini
  only for optional remote operator access.
- Hostnames (tailnet only):
  - `https://code.tailfd1400.ts.net/` → code-server (8080)
  - `https://chat.tailfd1400.ts.net/` → Open WebUI (3000)
  - `https://codeagent.tailfd1400.ts.net/` → OpenCode Web (4096)
  - `https://gateway.tailfd1400.ts.net/` → LiteLLM (4000)
  - `https://hands.tailfd1400.ts.net/` → OpenHands (4031)
  - `https://search.tailfd1400.ts.net/` → SearXNG (8888)
- Access is controlled by **grants** (not legacy ACLs). Use `svc:*` in `dst`.
- Internal Studio upstream path (current):
  - Studio OptiLLM uses Mini LiteLLM over LAN at `http://192.168.1.71:4000/v1`

## SearXNG search
- Local SearXNG: `http://127.0.0.1:8888/search?q=<query>&format=json`
- LiteLLM proxy: `http://127.0.0.1:4000/v1/search/searxng-search`
- Env: `SEARXNG_API_BASE=http://127.0.0.1:8888`
- Tool name: `searxng-search`
- OptiLLM `web_search` plugin also uses SearXNG when `SEARXNG_API_BASE` is set in `/etc/optillm-proxy/env`.

## Web fetch + clean (implemented, MCP stdio)
- Purpose: fetch a URL and return clean, model-ready text for summarization,
  RAG, or schema extraction.
- Implemented as MCP stdio tool (`services/mcp-tools/web-fetch`) exposing `web.fetch`
  and `search.web` (LiteLLM `/v1/search` backend). Invoked by an MCP client;
  not running as a systemd service yet.
- Recommended `web.fetch` stack: `httpx` + `trafilatura` (primary extraction)
  + `readability-lxml` (fallback) + `selectolax`/`lxml` (cleanup).
- Schematron note: it ignores prompts and uses only schema + input. Provide
  trimmed HTML or clean text for best extraction.

## OpenCode (client)
- Config: `~/.config/opencode/opencode.json`.
- Key file: `~/.config/opencode/litellm_api_key` (local-only secret).
- Provider: LiteLLM OpenAI-compatible.
  - On Mini: `baseURL=http://127.0.0.1:4000/v1`
  - On LAN devices: `baseURL=http://192.168.1.71:4000/v1`
  - Optional remote operator path: `https://gateway.tailfd1400.ts.net/v1`
- User-global config must already expose the `litellm` provider and the direct
  lanes `litellm/deep`, `litellm/main`, and `litellm/fast`.
- Repo-local OpenCode behavior in this repo is controlled by:
  - `opencode.json`
  - `.opencode/instructions/`
  - `.opencode/agents/`
  - `.opencode/skills/`
- Repo-local defaults:
  - default lane: `deep`
  - canary lane: `main`
  - synthesis-only lane: `fast`
  - approval prompts stay `ask` for `bash` and `edit`
- Current lane note: `main` (`qwen3-next-80b`) is the validated canary lane under
  `mlxctl` vLLM arg compilation.
  The locked live `8101` lane uses `tool_choice=auto`,
  `tool_call_parser=hermes`, and `reasoning_parser=null`.
- Approved rollout note:
  - MAIN canonical target is `Qwen3-Next-80B-A3B-Instruct` on `vllm-metal` at `8101`
  - explicit MAIN fallback remains dormant recovery metadata only
  - FAST and DEEP are now the settled GPT lanes on the shared `llmster`/llama.cpp service at `8126`
- Repo-shared OpenCode workflow and verification live in `docs/OPENCODE.md` and
  `docs/foundation/testing.md`.
- Repo-local durability workflow is stage-aware rather than universally
  ceremonial:
  - `Discover` and `Design` stay low-friction and read-only first
  - `Build` and `Verify` require the startup declaration before proposed edits
    or commands
  - `homelab-durability` and `homelab_durability` are equivalent invocation
    names
  - rollback is conditional to runtime risk, not universal for docs/discovery
- Root/doc placement hygiene is enforced separately by
  `scripts/repo_hygiene_audit.py`, with root-entry violations treated as the
  first blocking hygiene class.

## OpenCode Web (Mini)
- Service boundary: `services/opencode-web`.
- Bind: `http://127.0.0.1:4096` locally, `0.0.0.0:4096` at the listener.
- Tailnet operator URL: `https://codeagent.tailfd1400.ts.net/`
- Tailscale exposure: dedicated Service `svc:codeagent`
- Auth: HTTP Basic Auth from `/etc/opencode/env`.
- Runtime contract is repo-managed via `platform/ops/systemd/opencode-web.service`.
- Working directory is `/home/christopherbailey/homelab-llm`.
- Writable sandbox allowlist is intentionally narrow:
  - `/home/christopherbailey/homelab-llm`
  - `~/.local/share/opencode`
  - `~/.local/state/opencode`
  - `~/.cache/opencode`
- Approval prompts inside OpenCode do not override the service sandbox. Repo editability depends on `ReadWritePaths=` in the systemd unit.

## OpenHands (Mini, Phase A managed service)
- Service boundary: `services/openhands`.
- Primary launch path: repo-managed `systemd` + Docker on the Mini, published locally to `127.0.0.1:4031`.
- Repo-managed unit: `platform/ops/systemd/openhands.service`.
- Host runtime files: `/etc/systemd/system/openhands.service`, `/etc/openhands/env`.
- Tailnet operator path: `https://hands.tailfd1400.ts.net/` through `tailscale serve --service=svc:hands`.
- Workspace contract: mount only a disposable host path into `/workspace` via
  `SANDBOX_VOLUMES`; do not mount the live monorepo in Phase A.
- Model/provider contract in Phase A: temporary provider/API key entered in the
  OpenHands UI only. No repo config or LiteLLM wiring. `/etc/openhands/env`
  is limited to non-secret runtime vars only.
- Phase B worker contract is intentionally narrow:
  - reserved/internal alias only: `code-reasoning`
  - backend target behind LiteLLM: `deep`
  - OpenHands model string: `litellm_proxy/code-reasoning`
  - non-human service-account key only: `openhands-worker`
  - Chat Completions-first
  - MCP denied
  - `/v1/responses` denied
- Current runtime note:
  - canonical OpenHands container path is `http://host.docker.internal:4000/v1`
  - verified fallback/reference path is `http://192.168.1.71:4000/v1`
- Security posture: Docker sandbox only, operator-supervised, no GitHub
  integration, no deploy rights, no auto-merge, no LAN exposure, tailnet access
  limited to dedicated service `svc:hands`.

## OptiLLM proxy (deployed, not gateway-exposed)
- The Studio OptiLLM proxy remains deployed on `http://192.168.1.72:4020/v1`.
- It is not part of the active LiteLLM alias surface during this three-alias
  backend hardening phase.

## LiteLLM extension points (summary)
See `services/litellm-orch/docs/litellm-extension-points.md` for the hook map
and where this repo uses callbacks vs guardrails.

### GPT formatting ownership policy
- GPT formatting/tool-call parsing is upstream-first.
- `main` keeps the locked upstream `vllm-metal` parser render on `8101`
  (`tool_call_parser=hermes`, no reasoning parser).
- `fast`, `deep`, and reserved/internal worker alias `code-reasoning` keep the
  direct `llmster` / llama.cpp response shape as the canonical truth path.
- LiteLLM is no longer the canonical GPT response normalizer for these lanes.
- The one current LiteLLM exception is a small GPT request-default shim:
  when callers omit `reasoning_effort`, LiteLLM injects `reasoning_effort=low`
  for `fast`, `deep`, and `code-reasoning` because the current `llmster`
  service contract does not expose a server-side default knob for it.
- LiteLLM does not currently rewrite GPT response content, strip provider
  reasoning fields, or repair named/object-form forced-tool semantics.
- Current GPT contract remains Chat Completions-first:
  - ordinary tool calling supported
  - named/object-form forced-tool choice unsupported
  - strict structured-output guarantees not part of the supported contract

## OpenVINO backend (not wired in LiteLLM)
- Systemd unit: `/etc/systemd/system/ov-server.service` (binds `0.0.0.0` for maintenance).
- Env: `/etc/homelab-llm/ov-server.env` (runtime).
- Endpoints: `/health`, `/v1/models`, `/v1/chat/completions`.
- Ops: `/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl` controls model warm-up profiles.
- Status: available as a standalone backend; no LiteLLM handles are currently registered.

## OptiLLM optimization proxy
- Studio LAN proxy: `http://192.168.1.72:4020/v1` (binds `192.168.1.72:4020` on the Studio).
- Current usage: deployed but not exposed through the active LiteLLM alias surface.
- Requests do not require backend bearer auth on the Studio OptiLLM listener.
- Current upstream: Mini LiteLLM through the Mini LAN URL `http://192.168.1.71:4000/v1`.
- Upstream can be LiteLLM or MLX directly; avoid routing loops.
- Proxy providers config: `~/.optillm/proxy_config.yaml` must point only to
  LiteLLM to avoid cloud fallbacks.

### Gateway exposure note
- The current backend hardening phase does not expose any `boost*` aliases
  through LiteLLM.

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
{"model":"deep","messages":[{"role":"user","content":"ping"}],"optillm_approach":"moa"}
```

### Repo-local OpenCode workflow
1. Start from root `AGENTS.md` and `docs/OPENCODE.md`.
2. Use the repo-local `repo-deep` agent for grounded repo planning, review, and implementation work.
3. Use `repo-main` only as a canary lane that must fail closed if it cannot gather real repo evidence.
4. Use `repo-fast` only for drafting or synthesis from already-provided text.
5. Treat OptiLLM `boost*` aliases as a separate, opt-in path rather than the default OpenCode workflow.

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
- MCP registry lives at `/etc/homelab-llm/mcp-registry.json`.
- Template: `platform/ops/templates/mcp-registry.json`.
- Current registry scope is TinyAgents-facing stdio tools only.
- Keep tool calls separate from LiteLLM model calls.
- Plan a sandboxed `python.run` tool for future workflows; avoid unsandboxed
  execution by default.

## Open Terminal MCP (implemented locally)
- Current live path for terminal-style repo inspection is the localhost-only
  Open Terminal MCP backend, with direct Open WebUI registration on the Mini.
- Runtime:
  - backend: `http://127.0.0.1:8011/mcp`
  - transport: MCP streamable HTTP
- Scope:
  - bind mount only `/home/christopherbailey/homelab-llm:/lab/homelab-llm:ro`
  - no whole-host bind
  - no `docker.sock`
  - no write tools in slice 1
- Explicitly separate role:
  - Open WebUI native Open Terminal on `127.0.0.1:8010` is the interactive
    terminal path
  - Open WebUI also registers the localhost-only `127.0.0.1:8011/mcp` backend
    as a separate read-only MCP tool server for model tool use
  - current Open WebUI filter allowlist: `health_check`, `list_files`,
    `read_file`, `grep_search`, `glob_search`
  - current Open WebUI audience default is admin-only because the connection has
    no explicit access grants and the service still uses admin-bypass defaults
  - Open Terminal MCP is intentionally not added to the TinyAgents MCP registry
    in this slice
  - a shared LiteLLM MCP alias for the read-only subset remains follow-on work;
    direct Open WebUI wiring is current runtime truth
- OpenHands remains excluded:
  - worker alias `code-reasoning` stays MCP-denied
  - `/v1/responses` stays denied for the worker key

## Client base URL recommendation
- Prefer LAN when local: `http://192.168.1.71:4000/v1`.
- Local host-only calls on the Mini can still use `http://127.0.0.1:4000/v1`.
