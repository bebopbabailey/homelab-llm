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
- Caller-requested structured outputs pass through LiteLLM when the selected upstream supports them, but canonical `main` on the current Qwen backend is still failing both current non-stream direct `8101` structured-output request paths:
  - exact documented OpenAI-compatible `response_format.json_schema`
  - exact vLLM-native `structured_outputs.json`
  LiteLLM currently reproduces the same backend-visible failure text for the
  exact documented `response_format` path.
- LiteLLM does not inject web-search schemas, repair loops, or citation rendering.
- `drop_params=true` is part of the current runtime baseline.
- Active router fallback baseline is `fast -> main`.

## Backends (External Services)
- **OpenVINO LLM server** on the Mini (`http://localhost:9000`, supports `/health`, `/v1/models`, `/v1/chat/completions`)
- **MLX Studio lane** on the Studio: OpenAI-compatible `vllm-metal` (`vllm serve`)
  endpoint on **8101** bound to the Studio LAN IP
  (`http://192.168.1.72:8101/v1`) for public `main`.
- **Studio llmster GPT service** on the Studio: OpenAI-compatible shared GPT
  listener on **8126** (`http://192.168.1.72:8126/v1`) for public `fast` and `deep`.
- **Additional Studio operator infrastructure** on the Studio:
  non-core OptiLLM proxy on `4020` and the settled GPT-family service on `8126`.
- **Voice Gateway** on the Orin: OpenAI-compatible LAN speech facade at the configured
  `VOICE_GATEWAY_API_BASE`; Speaches stays localhost-only behind that facade.
- **AFM OpenAI-compatible API** on the Studio (planned; target **9999**)
- **SearXNG** on the Mini (`http://127.0.0.1:8888/search`) for the generic `searxng-search` tool.

## Default Logical Models
- `main` -> MLX Studio lane `8101`
- `deep` -> Studio `llmster` lane `8126` (`llmster-gpt-oss-120b-mxfp4-gguf`)
- `fast` -> Studio `llmster` lane `8126` (`llmster-gpt-oss-20b-mxfp4-gguf`)
- `voice-stt-canary` -> Orin `voice-gateway` facade (`whisper-1`)
- `voice-tts-canary` -> Orin `voice-gateway` facade (`tts-1`)
- `voice-stt` -> Orin `voice-gateway` facade (`whisper-1`)
- `voice-tts` -> Orin `voice-gateway` facade (`tts-1`)

## Current runtime notes
- Pushcut MCP integration is not active in the main LiteLLM runtime.
- Repo-local OpenCode default behavior is the direct `deep` lane as documented
  in `/home/christopherbailey/homelab-llm/docs/OPENCODE.md`.
- `main` routes to Studio lane `8101`, where the locked vLLM runtime keeps
  `tool_choice=auto`, `tool_call_parser=hermes`, and no reasoning parser.
- `main` is currently hardened around non-stream `tool_choice=auto`,
  long-context sanity, and concurrency. Forced-tool semantics are currently
  unsupported and non-blocking for public `main`, and structured outputs remain
  outside the accepted public `main` contract on the current `8101` runtime.
- `8126` is active for canonical `fast` plus public `deep`.
- `8123-8125` are retired shadow ports and are outside the active gateway alias
  surface.
- `4020` remains deployed for non-core operator use and is not part of the
  canonical public alias surface.
- There are no active temporary GPT canary aliases in the current gateway
  contract.
- GPT lanes remain Chat Completions-first in the current hardening phase.
- `/v1/responses` remains in validation scope for GPT lanes but is advisory
  unless a defect there also matters to the public Chat Completions path.
- Current public `deep` contract on the live shared `8126` backend:
  - plain chat / structured simple / structured nested clean
  - auto noop strong
  - auto arg-bearing strong on the present cutover run
  - `required` strong enough to satisfy constrained-mode acceptance
  - named forced-tool choice unsupported on the current backend path

## Logging (Planned)
- Request logging: JSONL via LiteLLM (`json_logs: true`) for ingestion (model, upstream, latency, status, error).
- Log destination: stdout/journald for now; switch to file output when ingestion pipeline is ready.

## Guardrails
- `transcribe-guardrail` is enabled for `task-transcribe` and `task-transcribe-vivid`.
  It strips wrappers/labels and removes reasoning fields from transcript outputs.
- `task-transcribe` and `task-transcribe-vivid` are text cleanup aliases only.
  They are not audio STT endpoints and must not be reused for Open WebUI speech wiring.
- `harmony-guardrail` is enabled in both `pre_call` and `post_call` for GPT lanes only
  (`deep`, `fast`):
  - `pre_call`: sanitizes prior `assistant` history turns by extracting Harmony `final`
    content when strict Harmony wire blocks are detected, and injects
    `reasoning_effort=low` when the caller did not provide one.
  - `post_call`: converts Harmony wire output to `final` only for client-visible response
    content and strips provider reasoning fields from GPT lane responses.
  - strict detection guard: no mutation unless real Harmony wire shape is present
    (`<|channel|>` + `<|message|>` + `analysis|final` channel).
  - streaming is pass-through by default; the guardrail does not coerce `stream=false`.
  - streaming iterator hook currently passes chunks through without post-normalization.
    strict Harmony final-content normalization remains strongest on non-stream responses.
  - Qwen lane (`main`) is passthrough for Harmony normalization.
  - GPT public-lane hardening currently assumes `reasoning_effort=low` unless
    the caller explicitly sets a different supported value.
- LiteLLM also carries a narrow Qwen `main` post-call success hook:
  - target: `main` only
  - non-stream only
  - `tool_choice=auto` only
  - activates only when the backend returns a single strict raw
    `<tool_call>...</tool_call>` block with no structured `tool_calls`
  - purpose: lossless conversion of a semantically correct raw tool block into
    a client-visible OpenAI-style `tool_calls` payload
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
- OpenHands Phase B remains delayed while backend hardening focuses on the three
  active public LLM lanes.
- Current LAN-reachable infra gateway path is `http://192.168.1.71:4000/v1`.
- Internal Studio MLX and Studio OptiLLM backends do not require backend bearer auth.

## Orchestration (Planned)
- TinyAgents will be a client of LiteLLM (not a direct backend caller).
- See `docs/tinyagents-integration.md` for IO flow and responsibility split.
