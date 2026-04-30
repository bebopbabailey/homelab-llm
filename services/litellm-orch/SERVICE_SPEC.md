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
- `DATABASE_URL` is required in the runtime environment for DB-backed LiteLLM
  auth/key-management features such as teams, groups, service accounts, and
  `/key/generate`.
- `MEMORY_API_BEARER_TOKEN` is required in the Mini LiteLLM runtime for
  `task-youtube-summary` transcript upserts and response-map writes against the
  Studio memory API. The token value must match the Studio-side file
  `MEMORY_API_WRITE_BEARER_TOKEN_FILE`.
- Current package baseline pins `litellm[proxy]==1.83.4`.
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
- **AFM OpenAI-compatible API** on the Studio (planned; target **9999**)
- **SearXNG** on the Mini (`http://127.0.0.1:8888/search`) for the generic `searxng-search` tool.

## Default Logical Models
- `deep` -> Studio `llmster` lane `8126` (`llmster-gpt-oss-120b-mxfp4-gguf`)
- `fast` -> Studio `llmster` lane `8126` (`llmster-gpt-oss-20b-mxfp4-gguf`)
- `code-reasoning` -> reserved internal OpenHands worker alias on the same
  `deep` backend lane (`llmster-gpt-oss-120b-mxfp4-gguf`)
- `code-qwen-agent` -> experimental internal OpenHands shadow alias through the
  Mini-local `qwen-agent-proxy` sidecar (`qwen-agent-coder-next-shadow`)
- `task-transcribe` -> Studio `llmster` fast lane `8126`
  (`llmster-gpt-oss-20b-mxfp4-gguf`) with the standard transcript-cleanup prompt
- `task-transcribe-vivid` -> Studio `llmster` deep lane `8126`
  (`llmster-gpt-oss-120b-mxfp4-gguf`) with the vivid transcript-cleanup prompt
- `task-json` -> Studio `llmster` fast lane `8126`
  (`llmster-gpt-oss-20b-mxfp4-gguf`) with the transcript-to-JSON extraction prompt
- `task-youtube-summary` -> Studio `llmster` deep lane `8126`
  (`llmster-gpt-oss-120b-mxfp4-gguf`) with the YouTube transcript-summary prompt
- `voice-stt-canary` -> Orin `voice-gateway` facade (`whisper-1`)
- `voice-tts-canary` -> Orin `voice-gateway` facade (`tts-1`)
- `voice-stt` -> Orin `voice-gateway` facade (`whisper-1`)
- `voice-tts` -> Orin `voice-gateway` facade (`tts-1`)

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
  path for `fast`, `deep`, `task-transcribe`, `task-transcribe-vivid`,
  `task-json`, and `task-youtube-summary`.
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
  Its pre-call path only normalizes transcript punctuation, sets the
  transcribe `prompt_id`, and constrains the Responses token budget enough for
  the `fast` lane to emit final text; its post-call path strips wrappers/labels
  and rewrites task outputs into clean transcript-only payloads.
- `task-transcribe` and `task-transcribe-vivid` are text cleanup aliases only.
  Their canonical contract is `POST /v1/responses` with native Responses `input`,
  not `POST /v1/audio/transcriptions`,
  and must not be reused for Open WebUI speech wiring.
- The transcribe dotprompt files are rendered through the generic
  `prompt-pre` template path. They do not select a backend model; router alias
  selection stays authoritative.
- `task-transcribe-vivid` accepts optional `prompt_variables.audience` and
  `prompt_variables.tone` for subtle punctuation/paragraph shaping only.
  It is also the supported multi-turn transcript-manipulation lane:
  callers may reuse the returned response `id` as `previous_response_id` on
  later `/v1/responses` calls. The echoed `previous_response_id` in gateway
  responses is not a stable public identity surface and may differ from the
  public `id` string that the caller originally stored.
- `task-json` is a transcript-to-JSON utility alias only.
  Its canonical contract is `POST /v1/responses` with native Responses `input`.
  It removes tool-calling fields and returns minified JSON with exact top-level keys
  `todo`, `grocery`, `purchase`, and `other`.
- `task-json` uses LiteLLM-owned pre-call and post-call guardrails to inject a
  fixed strict `json_schema`, normalize malformed/provider-sloppy payloads,
  salvage unknown categories into `other`, and fall back once to the canonical
  empty payload with `other.attributes.guardrail_status="repair_failed"` if repair fails.
- `task-youtube-summary` is a YouTube transcript-summary utility alias.
  Its canonical initial contract is `POST /v1/responses` with native Responses
  `input` containing one supported YouTube video URL and an optional short ask.
  `POST /v1/chat/completions` remains compatibility-only for Open WebUI and
  other chat-style clients.
- `task-youtube-summary` uses a LiteLLM-owned pre-call guardrail to normalize
  the first-turn URL, fetch source-faithful structured transcript data from the
  localhost-only `media-fetch-mcp` service on `127.0.0.1:8012/mcp`,
  synchronously upsert a durable transcript document through the memory API,
  and render the adaptive summary dotprompt through the generic `prompt-pre`
  path. `segments[]` from `media-fetch-mcp` are the canonical chunking/indexing
  surface; LiteLLM does not reparse timestamped transcript text for that work.
- `task-youtube-summary` emits readable markdown with a compact metadata line,
  adaptive sections, and sparse timestamps. The first summary line includes the
  durable document handle (`Document: youtube:<video_id>`). Successful
  Responses payloads are rewritten into stable `output_text` while preserving
  response `id`,
  `previous_response_id`, and `usage`.
- `task-youtube-summary` accepts common single-video YouTube watch, short-link,
  Shorts, and live URLs. Playlist-only, channel, search, and other non-video
  pages are rejected.
- `task-youtube-summary` fails closed when YouTube does not expose a usable
  caption track. v1 does not add ASR fallback or metadata-only summary mode.
- `task-youtube-summary` keeps English summary/answer output as the default
  user contract even when `media-fetch-mcp` returns a non-English transcript;
  translation remains a summarization concern, not a transcript-service
  concern.
- `task-youtube-summary` supports direct follow-up Q&A on the same alias.
  `previous_response_id` is treated as an ergonomic handle only; LiteLLM
  resolves it into a retrieval-owned `document_id` mapping and asks the memory
  API for document-scoped transcript chunks before follow-up synthesis.
  Oversized transcripts are still summarized internally on `deep`, but their
  follow-ups now ground against the indexed transcript document rather than
  provider-side placeholder lineage.
- Chat-completions follow-ups must not require a repeated URL. When
  `previous_response_id` is absent, LiteLLM attempts recovery in this order:
  explicit `document_id`, prior assistant metadata line, then prior YouTube URL
  in chat history; otherwise it fails clearly and asks for the URL or document
  handle.
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
    `code-reasoning`, `task-transcribe`, `task-transcribe-vivid`, `task-json`,
    and `task-youtube-summary`
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
  - `deep`, `fast`, `task-transcribe`, `task-transcribe-vivid`, `task-json`,
    and `task-youtube-summary` all accept `POST /v1/responses`
  - `POST /v1/chat/completions` remains compatibility-only during the current migration window
  - raw upstream `fast` / `deep` callers should treat the Responses `output`
    message surface as canonical text; `output_text` is advisory-only on direct
    `llmster`
  - task aliases preserve response `id`, `previous_response_id`, and `usage`
    while also returning stable `output_text` for client ergonomics; callers
    may reuse the public `id` on follow-up input, but should not require the
    echoed `previous_response_id` string to match that public value verbatim
  - `chatgpt-5` follows its adapter-backed dual-endpoint path rather than the local GPT request-default shim
  - `chatgpt-5` follows the Codex-backed sidecar path rather than the local GPT
    request-default shim
  - ordinary tool calling is accepted on compatible GPT-OSS lanes
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
