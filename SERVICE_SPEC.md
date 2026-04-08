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
- Current package baseline pins `litellm[proxy]==1.83.4`.
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
- `code-reasoning` -> reserved internal OpenHands worker alias on the same
  `deep` backend lane (`llmster-gpt-oss-120b-mxfp4-gguf`)
- `task-transcribe` -> MLX Studio lane `8101`
  (`mlx-qwen3-next-80b-mxfp4-a3b-instruct`) with the standard transcript-cleanup prompt
- `task-transcribe-vivid` -> MLX Studio lane `8101`
  (`mlx-qwen3-next-80b-mxfp4-a3b-instruct`) with the vivid transcript-cleanup prompt
- `task-json` -> Studio `llmster` fast lane `8126`
  (`llmster-gpt-oss-20b-mxfp4-gguf`) with the transcript-to-JSON extraction prompt
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
- The local canonical public trio remains `main`, `deep`, and `fast`.
- No ChatGPT-backed public aliases are part of the accepted gateway contract on
  the current stable LiteLLM runtime.
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
  They are invoked through `POST /v1/chat/completions`, not `POST /v1/audio/transcriptions`,
  and must not be reused for Open WebUI speech wiring.
- `task-transcribe-vivid` accepts optional `prompt_variables.audience` and
  `prompt_variables.tone` for subtle punctuation/paragraph shaping only.
- `task-json` is a transcript-to-JSON utility alias only.
  It is invoked through `POST /v1/chat/completions`, forces non-streaming,
  removes tool-calling fields, and returns minified JSON with exact top-level keys
  `todo`, `grocery`, `purchase`, and `other`.
- `task-json` uses LiteLLM-owned pre-call and post-call guardrails to inject a
  fixed strict `json_schema`, normalize malformed/provider-sloppy payloads,
  salvage unknown categories into `other`, and fall back once to the canonical
  empty payload with `other.attributes.guardrail_status="repair_failed"` if repair fails.
- GPT formatting ownership is upstream-first:
  - `main` keeps the locked upstream parser render on `8101`
    (`tool_choice=auto`, `tool_call_parser=hermes`, no reasoning parser).
  - `fast`, `deep`, and internal worker alias `code-reasoning` keep upstream
    `llmster` / llama.cpp response formatting and tool-call structure as the
    canonical truth path.
  - LiteLLM does not own GPT response rewriting for these lanes.
- LiteLLM retains one narrow GPT request-default shim only:
  - `gpt-request-defaults` runs `pre_call` for `deep`, `fast`, and
    `code-reasoning`
  - behavior: inject `reasoning_effort=low` only when the caller omitted it
  - no assistant-history rewriting
  - no post-call content extraction
  - no provider reasoning-field stripping
  - no forced `stream=false`
- `code-reasoning` inherits the same upstream GPT normalization path as `deep`.
- Current supported GPT contract remains Chat Completions-first:
  - ordinary tool calling is supported
  - named/object-form forced-tool choice is unsupported on the current GPT
    backend family
  - strict structured-output guarantees are not part of the supported GPT or
    OpenHands worker contract
- No web-search-specific pre-call or post-call guardrails are active in LiteLLM.
- A Mini-side Prisma/schema repair was required on the current LiteLLM 1.83.4
  deployment because the deployed Postgres schema had drifted behind the shipped
  Prisma client. `_prisma_migrations`, `LiteLLM_ToolTable`,
  `LiteLLM_ConfigOverrides`, and `LiteLLM_VerificationToken.agent_id` /
  `.project_id` were restored by running LiteLLM's own startup DB setup path and
  then regenerating Prisma Client Python in the service venv.
- The repo-managed systemd unit must keep
  `ENFORCE_PRISMA_MIGRATION_CHECK=true` so future drift fails fast at startup
  instead of surfacing later as partial MCP/key-management breakage.
- ChatGPT provider auth uses LiteLLM's own device-code/OAuth login flow on first
  use, but the current stable 1.83.4 Mini runtime still fails real
  `chatgpt/...` inference after auth with `ChatgptException - Unknown items in
  responses API response: []`. Do not treat ChatGPT aliases as an accepted
  Open WebUI contract on this baseline.

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
- ChatGPT auth state must stay out of git. By default LiteLLM stores it at
  `~/.config/litellm/chatgpt/auth.json` for the service user. Runtime-only
  overrides may use `CHATGPT_TOKEN_DIR` and `CHATGPT_AUTH_FILE`, but that auth
  state alone does not make ChatGPT aliases production-ready on the current
  stable runtime.
- DB-backed team and service-account endpoints are live in the deployed proxy.
- OpenHands Phase B uses one reserved internal worker alias only:
  `code-reasoning`.
- `code-reasoning` is not a public human lane. It is the governed OpenHands
  worker alias and tracks the current `deep` backend lane behind LiteLLM.
- Current worker-key contract for OpenHands is:
  - service-account key only
  - models allowlist: `code-reasoning`
  - allowed routes:
    - `/v1/models`
    - `/v1/model/info`
    - `/model/info`
    - `/v1/chat/completions`
  - denied by route policy:
    - `/v1/mcp/*`
    - `/v1/responses`
- Same-host direct access to `127.0.0.1:8011/mcp` is not part of the client
  contract; LiteLLM remains the canonical authenticated surface once the shared
  MCP lane is validated on a stable runtime.
- Current LAN-reachable infra gateway path is `http://192.168.1.71:4000/v1`.
- Current OpenHands container contract is `http://host.docker.internal:4000/v1`,
  with `http://192.168.1.71:4000/v1` retained as the verified fallback/reference
  path.
- Internal Studio MLX and Studio OptiLLM backends do not require backend bearer auth.

## Orchestration (Planned)
- TinyAgents will be a client of LiteLLM (not a direct backend caller).
- See `docs/tinyagents-integration.md` for IO flow and responsibility split.
