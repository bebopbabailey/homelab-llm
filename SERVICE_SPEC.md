# Service Spec: litellm-orch

## Purpose
OpenAI-compatible gateway for clients. This service owns routing, auth,
retries, fallbacks, and generic tool/search proxying only; it does not
implement inference or web-search business logic.

## Host & Runtime
- **Host**: Mac mini (Intel i7, 64 GB RAM), Ubuntu 24.04
- **Language/Framework**: Python 3.12, LiteLLM proxy behavior, FastAPI + Uvicorn
- **Inference**: None (upstream only)
- **Bind**: `0.0.0.0:4000` (localhost remains valid; canonical infra path is
  `http://192.168.1.71:4000/v1`)

## Endpoints
- `POST /v1/chat/completions` (OpenAI-compatible; forwards to upstream)
- `POST /v1/responses` (OpenAI-compatible Responses API; supports LiteLLM MCP tool use)
- `POST /v1/audio/transcriptions` (OpenAI-compatible; routes speech STT aliases)
- `POST /v1/audio/speech` (OpenAI-compatible; routes speech TTS aliases)
- `POST /v1/search/<tool_name>` (direct callers and MCP tools)
- `GET /v1/models` (logical model names from router config)
- `GET /v1/model/info` (logical model capability metadata; current OpenHands uses this path for `litellm_proxy/<alias>` discovery)
- `GET /health` (LiteLLM health check across configured deployments)
- `GET /health/readiness` and `GET /health/liveliness` (service readiness/liveness)
- `GET /metrics/` (Prometheus; currently open in deployment; **use trailing slash**)

## Configuration
- Declarative routing in `config/router.yaml` with env-var substitution.
- Environment variables supply upstream base URLs and runtime options.
- Example envs live in `config/env.example`.
- For long-running service use, load env vars explicitly (for example systemd `EnvironmentFile=config/env.local`).
- Custom guardrails are declared in `config/router.yaml` under `guardrails`.
- Caller-requested structured outputs pass through LiteLLM when the selected upstream supports them.
- LiteLLM does not inject web-search schemas, repair loops, or citation rendering.
- `drop_params=true` is part of the current runtime baseline.
- Active router fallback baseline is `fast -> main`.

## Backends (External Services)
- **OpenVINO LLM server** on the Mini (`http://localhost:9000`, supports `/health`, `/v1/models`, `/v1/chat/completions`)
- **MLX Studio lanes** on the Studio: OpenAI-compatible per-port `vllm-metal` (`vllm serve`)
  endpoints on **8100/8101/8102** bound to the Studio LAN IP
  (`http://192.168.1.72:<port>/v1`).
- **Voice Gateway** on the Orin: OpenAI-compatible LAN speech facade at the configured
  `VOICE_GATEWAY_API_BASE`; Speaches stays localhost-only behind that facade.
- **AFM OpenAI-compatible API** on the Studio (planned; target **9999**)
- **SearXNG** on the Mini (`http://127.0.0.1:8888/search`) for the generic `searxng-search` tool.

## Default Logical Models
- `main` -> MLX Studio lane `8101`
- `code-reasoning` -> MLX Studio lane `8101` (stable OpenHands worker alias)
- `deep` -> MLX Studio lane `8100`
- `fast` -> MLX Studio lane `8102`
- `boost` -> Studio OptiLLM proxy on `:4020` (optimization lane)
- `voice-stt-canary` -> Orin `voice-gateway` facade (`whisper-1`)
- `voice-tts-canary` -> Orin `voice-gateway` facade (`tts-1`)
- `voice-stt` -> Orin `voice-gateway` facade (`whisper-1`)
- `voice-tts` -> Orin `voice-gateway` facade (`tts-1`)

## Current runtime notes
- Pushcut MCP integration is not active in the main LiteLLM runtime.
- Repo-local OpenCode default behavior is the direct `deep` lane as documented
  in `/home/christopherbailey/homelab-llm/docs/OPENCODE.md`.
- `boost*` aliases remain gateway-exposed OptiLLM routes, but they are not the
  default repo-local OpenCode control plane.
- `main` routes to Studio lane `8101`, where the locked vLLM runtime keeps
  `tool_choice=auto`, `tool_call_parser=llama3_json`, and no reasoning parser.

## Logging (Planned)
- Request logging: JSONL via LiteLLM (`json_logs: true`) for ingestion (model, upstream, latency, status, error).
- Log destination: stdout/journald for now; switch to file output when ingestion pipeline is ready.

## Guardrails
- `transcribe-guardrail` is enabled for `task-transcribe` and `task-transcribe-vivid`.
  It strips wrappers/labels and removes reasoning fields from transcript outputs.
- `task-transcribe` and `task-transcribe-vivid` are text cleanup aliases only.
  They are not audio STT endpoints and must not be reused for Open WebUI speech wiring.
- `harmony-guardrail` is enabled in both `pre_call` and `post_call` for GPT lanes only
  (`deep`, `fast`, `boost`, `boost-deep`, `boost-plan`, `boost-plan-trio`,
  `boost-plan-verify`, `boost-ideate`, `boost-fastdraft`):
  - `pre_call`: sanitizes prior `assistant` history turns by extracting Harmony `final`
    content when strict Harmony wire blocks are detected.
  - `post_call`: converts Harmony wire output to `final` only for client-visible response
    content.
  - strict detection guard: no mutation unless real Harmony wire shape is present
    (`<|channel|>` + `<|message|>` + `analysis|final` channel).
  - streaming is pass-through by default; the guardrail does not coerce `stream=false`.
  - streaming iterator hook currently passes chunks through without post-normalization.
    strict Harmony final-content normalization remains strongest on non-stream responses.
  - Qwen lane (`main`) is passthrough for Harmony normalization.
- No web-search-specific pre-call or post-call guardrails are active in LiteLLM.

## Search Ownership Boundary
- Open WebUI owns web-search UX plus provider/loader configuration.
- LiteLLM owns routing/auth/retries/fallbacks and generic `/v1/search/<tool_name>` access only.
- vLLM owns inference and explicit structured decoding only when the caller requests it.

## Service Management (Planned)
- User systemd service with explicit port binding

## Auth (Current)
- API key enforcement is enabled for `/v1/*` and `/health`.
- `/health/readiness`, `/health/liveliness`, and `/metrics/` are currently open.
- Keys are loaded from `config/env.local` by systemd `EnvironmentFile`.
- DB-backed team and service-account endpoints are live in the deployed proxy.
- OpenHands Phase B must use a team-owned service-account key, not a human key.
- Verified OpenHands capability discovery path is `GET /v1/model/info`.
- Current live build returns filterable single-model data by `litellm_model_id`;
  `?model=code-reasoning` is not a single-model filter in the deployed proxy.
- Current deployment enforces `allowed_routes` for service-account keys, and the
  validated OpenHands worker is limited to `/v1/models`, `/v1/model/info`, and
  `/v1/chat/completions`.
- Minimum OpenHands worker policy is one model allowlist (`code-reasoning`) plus
  verified MCP denial.
- Current LAN-reachable infra gateway path is `http://192.168.1.71:4000/v1`.
- Internal Studio MLX and Studio OptiLLM backends do not require backend bearer auth.

## Orchestration (Planned)
- TinyAgents will be a client of LiteLLM (not a direct backend caller).
- See `docs/tinyagents-integration.md` for IO flow and responsibility split.
