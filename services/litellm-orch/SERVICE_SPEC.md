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
- `POST /v1/audio/transcriptions` (OpenAI-compatible request/JSON-text response
  boundary; provider-specific format capabilities vary by STT alias)
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
- `DATABASE_URL` is required in the runtime environment for DB-backed LiteLLM
  auth/key-management features such as teams, groups, service accounts, and
  `/key/generate`.
- Current package baseline pins `litellm[proxy,stt-nvidia-riva]==1.85.0`
  with explicit stable NumPy and gRPC bounds for the Riva STT client path.
- Custom guardrails are declared in `config/router.yaml` under `guardrails`.
- Caller-requested structured outputs pass through LiteLLM when the selected
  upstream supports them. `task-json` remains the fixed-schema utility alias
  owned by LiteLLM guardrails in this service.
- LiteLLM does not inject web-search schemas, repair loops, or citation rendering.
- `drop_params=true` is part of the current runtime baseline.
- Active router fallback baseline is `fast -> deep`.
## Backends (External Services)
- **OpenVINO LLM server** on the Mini (`http://localhost:9000`, supports `/health`, `/v1/models`, `/v1/chat/completions`)
- **Studio llmster GPT service** on the Studio: OpenAI-compatible shared GPT
  listener on **8126** (`http://192.168.1.72:8126/v1`) for public `fast` and `deep`.
- **Additional Studio operator infrastructure** on the Studio:
  non-core OptiLLM proxy on `4020` and the settled GPT-family service on `8126`.
- **Voice Gateway** on the Orin: OpenAI-compatible LAN speech facade at the configured
  `VOICE_GATEWAY_API_BASE`; Speaches stays localhost-only behind that facade.
- **Studio Argmax/WhisperKit ASR** on the Studio: OpenAI-compatible
  transcription backend at the configured `ARGMAX_WHISPERKIT_API_BASE`.
- **Orin NVIDIA Riva ASR** on the Orin: self-hosted Riva gRPC backend at the
  configured `NVIDIA_RIVA_API_BASE`, source-restricted to Mini by the Orin
  `homelab-riva-grpc-firewall.service`.
- **AFM OpenAI-compatible API** on the Studio (planned; target **9999**)
- **SearXNG** on the Mini (`http://127.0.0.1:8888/search`) for the generic `searxng-search` tool.
- **YouTube Transcript API** on the Mini (`http://127.0.0.1:8014/v1`) for the
  `task-youtube-transcript` utility alias.

## Default Logical Models
- `deep` -> Studio `llmster` lane `8126` (`llmster-gpt-oss-120b-mxfp4-gguf`)
- `fast` -> Studio `llmster` lane `8126` (`llmster-gpt-oss-20b-mxfp4-gguf`)
- `code-reasoning` -> reserved internal OpenHands worker alias on the same
  `deep` backend lane (`llmster-gpt-oss-120b-mxfp4-gguf`)
- `code-qwen-agent` -> experimental internal OpenHands shadow alias through the
  Mini-local `qwen-agent-proxy` sidecar (`qwen-agent-coder-next-shadow`)
- `task-transcribe` -> Studio `llmster` fast lane `8126`
  (`llmster-gpt-oss-20b-mxfp4-gguf`); deprecated legacy text alias pending a
  later explicit pruning story, with no verified cleanup/output contract
- `task-json` -> Studio `llmster` fast lane `8126`
  (`llmster-gpt-oss-20b-mxfp4-gguf`) with the transcript-to-JSON extraction prompt
- `task-youtube-transcript` -> Mini-local `youtube-transcript-api`
  (`openai/youtube-transcript`) for source-faithful YouTube transcript retrieval
- `voice-stt-canary` -> Orin `voice-gateway` facade (`whisper-1`) for raw STT
- `voice-stt` -> Orin `voice-gateway` facade (`whisper-1`) for raw STT
- `personal-asr-whisperkit` -> Studio Argmax/WhisperKit ASR
  (`openai/large-v3-v20240930_626MB`) as the preserved personal-ASR baseline
- `personal-asr-riva` -> Orin NVIDIA Riva ASR
  (`nvidia_riva/conformer-en-US-asr-streaming-asr-bls-ensemble`) for the
  clean Riva-first personal transcription contract. It returns the normal JSON
  text shape; `prompt` is ignored, SRT requests return JSON text, and requested
  verbose word timestamps are not exposed by the proven native route.

## Current runtime notes
- Pushcut MCP integration is not active in the main LiteLLM runtime.
- Repo-local OpenCode default behavior is the direct `deep` lane as documented
  in `/home/christopherbailey/homelab-llm/docs/OPENCODE.md`.
- `8126` is active for canonical `fast` plus public `deep`.
- `8123-8125` are retired shadow ports and are outside the active gateway alias
  surface.
- `4020` remains deployed for non-core operator use and is not part of the
  canonical public alias surface.
- There are no active temporary GPT canary aliases in the current gateway
  contract.
- The local canonical public human lanes remain `deep` and `fast`.
- Additive experimental Codex-backed alias is `chatgpt-5`.
- `chatgpt-5` now routes through the Mini-local `ccproxy-api` sidecar instead
  of the raw `chatgpt.com/backend-api/codex` path.
- The current validated upstream model for that alias is `gpt-5.3-codex`.
- Public GPT-OSS lanes are Responses-first on the LiteLLM path.
- `POST /v1/chat/completions` remains temporarily available as a compatibility
  path for `fast`, `deep`, `task-transcribe`, and `task-json`.
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
- No `transcribe-guardrail` is active. The old transcribe-stack request
  shaping and direct personal-ASR input checks have been removed from the
  LiteLLM guardrail path.
- `task-transcribe` is a deprecated legacy text alias. Its audio behavior and
  prior cleanup/output guarantees are no longer part of the service contract;
  direct ASR callers use `personal-asr-riva` or `personal-asr-whisperkit`.
- The transcribe dotprompt is registered in LiteLLM's native `prompts:`
  config. No legacy transcribe guardrail supplies prompt variables, personal-ASR
  request checks, or wrapper-field cleanup.
- `task-json` is a transcript-to-JSON utility alias only.
  Its canonical contract is `POST /v1/responses` with native Responses `input`.
  It does not accept audio uploads. Audio callers first transcribe with
  `personal-asr-riva` or `personal-asr-whisperkit`, then submit the returned
  text to text-mode `task-json`.
  It removes tool-calling fields and returns minified JSON with exact top-level keys
  `todo`, `grocery`, `purchase`, and `other`.
- `task-json` uses LiteLLM-owned pre-call and post-call guardrails to inject a
  fixed strict `json_schema`, normalize malformed/provider-sloppy payloads,
  salvage unknown categories into `other`, and fall back once to the canonical
  empty payload with `other.attributes.guardrail_status="repair_failed"` if repair fails.
- `task-youtube-transcript` is a Chat Completions utility alias routed to the
  Mini-local `youtube-transcript-api` OpenAI-compatible backend. The latest
  user message must contain exactly one supported YouTube URL. The assistant
  message content is plain timestamped transcript text. LiteLLM does not use a
  custom guardrail, MCP orchestration, vector upsert, summarization, or
  follow-up recovery for this alias.
- GPT formatting ownership is upstream-first:
  - `fast`, `deep`, and internal worker alias `code-reasoning` keep upstream
    `llmster` / llama.cpp response formatting and tool-call structure as the
    canonical truth path.
  - LiteLLM now owns one narrow llmster repair path only for `deep`, `fast`,
    and `code-reasoning`: if a tool-bearing auto-tool response leaks raw
    internal tool protocol instead of returning structured `tool_calls`,
    LiteLLM forces non-streaming, rewrites the response into a valid tool call
    when the payload is lossless, and otherwise returns a clean assistant error
    instead of leaving Open WebUI in a half-finished tool turn.
- LiteLLM retains one narrow GPT request-default shim only:
  - `gpt-request-defaults` runs `pre_call` for `deep`, `fast`,
    `code-reasoning`, `task-transcribe`, and `task-json`
  - behavior:
    - inject `reasoning_effort=low` only when omitted on Chat Completions
    - inject `reasoning: {"effort":"low"}` only when omitted on Responses
  - justification: direct shared `8126` GPT-OSS Responses and Chat Completions
    still degrade on some omitted-effort probes
  - no assistant-history rewriting
  - no post-call content extraction
  - no provider reasoning-field stripping
  - no general forced `stream=false`
- LiteLLM also retains one llmster tool-call contract shim:
  - `llmster-toolcall-guardrail` runs `pre_call` and `post_call` for `deep`,
    `fast`, and `code-reasoning`
  - behavior: force `stream=false` only for tool-bearing `tool_choice=auto`
    requests, normalize leaked `to=functions...<|message|>{...}` protocol into
    OpenAI-compatible `tool_calls`, and fail closed to a clean assistant retry
    error when normalization is not lossless
- `code-reasoning` inherits the same upstream GPT normalization path as `deep`.
- Current supported public GPT-OSS contract is Responses-first:
  - `deep`, `fast`, `task-transcribe`, and `task-json` all accept `POST /v1/responses`
  - `POST /v1/chat/completions` remains compatibility-only during the current migration window
  - raw upstream `fast` / `deep` callers should treat the Responses `output`
    message surface as canonical text; `output_text` is advisory-only on direct
    `llmster`
  - deterministic `stream=false` / `temperature=0.0` normalization is scoped to
    supported task guardrail paths, not raw `fast` / `deep` lanes
  - `chatgpt-5` follows its adapter-backed dual-endpoint path rather than the local GPT request-default shim
  - `chatgpt-5` follows the Codex-backed sidecar path rather than the local GPT
    request-default shim
  - ordinary tool calling is accepted on compatible GPT-OSS lanes
  - named/object-form forced-tool choice is unsupported on the current GPT
    backend family
  - strict structured-output guarantees are not part of the supported GPT or
    OpenHands worker contract
- No web-search-specific pre-call or post-call guardrails are active in LiteLLM.
- `personal-asr-whisperkit` and `personal-asr-riva` are direct LiteLLM audio
  transcription aliases. No legacy transcribe guardrail owns personal-ASR
  provider behavior.
- A Mini-side Prisma/schema repair was originally required on the LiteLLM
  `1.83.4` deployment because the deployed Postgres schema had drifted behind
  the shipped Prisma client. The current package baseline is `1.85.0`.
  `_prisma_migrations`, `LiteLLM_ToolTable`,
  `LiteLLM_ConfigOverrides`, and `LiteLLM_VerificationToken.agent_id` /
  `.project_id` were restored by running LiteLLM's own startup DB setup path and
  then regenerating Prisma Client Python in the service venv.
- The repo-managed systemd unit must keep
  `ENFORCE_PRISMA_MIGRATION_CHECK=true` so future drift fails fast at startup
  instead of surfacing later as partial MCP/key-management breakage.
- `chatgpt-5` now uses `ccproxy-api` with local Codex auth state and a local
  bearer token. Auth state and service tokens must remain local-only and out of
  git.

## Search Ownership Boundary
- Open WebUI owns web-search UX plus provider/loader configuration.
- LiteLLM owns routing/auth/retries/fallbacks and generic `/v1/search/<tool_name>` access only.
- vLLM owns inference and explicit structured decoding only when the caller requests it.

## Service Management (Planned)
- User systemd service with explicit port binding

## Auth (Current)
- API key enforcement is enabled for `/v1/*` and `/health`.
- `/health/readiness`, `/health/liveliness`, and `/metrics/` are currently open.
- For this deployment, `/health/readiness` is not considered healthy when the
  JSON body reports `db: "Not connected"`, even if the endpoint still returns
  HTTP `200`.
- Keys are loaded from `config/env.local` by systemd `EnvironmentFile`.
- `chatgpt-5` no longer uses LiteLLM's raw ChatGPT backend path. Instead,
  LiteLLM calls the Mini-local `ccproxy-api` sidecar with a local bearer token,
  while CCProxy uses local Codex auth state. None of that auth material may be
  committed.
- DB-backed team and service-account endpoints are live in the deployed proxy.
- DB-backed auth depends on the Prisma/Postgres path being connected at runtime;
  when it is not, non-master keys fail before model routing with
  `type=no_db_connection`.
- OpenHands Phase B uses one reserved internal worker alias only:
  `code-reasoning`.
- `code-reasoning` is not a public human lane. It is the governed OpenHands
  worker alias and tracks the current `deep` backend lane behind LiteLLM.
- `code-qwen-agent` is an experimental shadow OpenHands alias only. It is not a
  public human lane and must not replace `code-reasoning` without a separate
  promotion pass.
- Current verified scope for `code-qwen-agent` is worker-key `models` plus
  `chat/completions`; worker-key `model/info` is still blocked on the shadow
  LiteLLM instance.
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
- Shadow validation may also use a separate localhost-only LiteLLM instance on
  `127.0.0.1:4001` with the same OpenHands container path shape via
  `host.docker.internal:4001`.
- Internal Studio MLX and Studio OptiLLM backends do not require backend bearer auth.

## Orchestration (Planned)
- TinyAgents will be a client of LiteLLM (not a direct backend caller).
- See `docs/tinyagents-integration.md` for IO flow and responsibility split.
