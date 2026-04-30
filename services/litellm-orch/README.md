# litellm-orch

OpenAI-compatible gateway that forwards requests to external backends. This
service owns routing, auth, retries, fallbacks, and generic tool/search proxying
only; it does not implement inference.

## Scope
- Gateway only; no inference in this repo.
- Declarative routing via `config/router.yaml` with env-var substitution.
- Logical handles use stable client-facing names; upstream OpenAI-compatible
  backends use `openai/<base-model>` in `litellm_params.model`.

## Runtime Contract
- Bind: `0.0.0.0:4000`
- On-host callers may keep using `127.0.0.1:4000`
- Canonical Studio upstream path: `http://192.168.1.71:4000/v1`
- Auth: API key enforcement is active for `/v1/*` and `/health`
- Open `/health/readiness`, `/health/liveliness`, and `/metrics/` remain part of
  the current runtime contract

## Backends
- Studio `llmster` GPT service on `8126` for `fast` and `deep`
- `task-transcribe` is a text-cleanup alias on `fast`
- `task-transcribe-vivid` is a text-cleanup alias on `deep`
- `task-youtube-summary` is a YouTube transcript-summary alias on `deep`
- Voice Gateway on the Orin for speech aliases
- SearXNG on the Mini for generic search tooling

## OpenCode Note
- Repo-local OpenCode defaults and agent/skill behavior are documented in
  `/home/christopherbailey/homelab-llm/docs/OPENCODE.md`.
- The local canonical public human lanes remain `fast` and `deep`.
- Public GPT-OSS traffic is Responses-first through LiteLLM for `fast`,
  `deep`, `task-transcribe`, `task-transcribe-vivid`, `task-json`, and
  `task-youtube-summary`.
- `POST /v1/chat/completions` remains a temporary compatibility path for the
  GPT-OSS public aliases during the current migration window.
- `chatgpt-5` keeps its own adapter-backed dual-endpoint behavior.
- `chatgpt-5` now routes through the Mini-local `ccproxy-api` Codex sidecar.
- `task-transcribe` and `task-transcribe-vivid` are additional task aliases,
  not part of the public human chat-lane trio.
- Their prompts are rendered through the generic `prompt-pre` dotprompt path;
  the transcribe guardrail only normalizes transcript input and strips wrapper
  fields from the final response payload.
- `task-youtube-summary` is also an additional task alias, not part of the
  public human chat-lane trio. Its guardrail resolves one supported YouTube
  video URL on the first turn, fetches structured transcript data from the
  localhost-only `media-fetch-mcp` service on `127.0.0.1:8012/mcp`, indexes a
  durable transcript document through the memory API, renders an adaptive
  summary prompt, and rewrites Responses output into stable `output_text`.
- Raw `fast` / `deep` Responses should be treated as `output`-first payloads;
  upstream `output_text` is not guaranteed to be populated on every direct
  `llmster` response.
- The task aliases keep a more ergonomic contract by returning stable
  `output_text`, preserving response `id`, and passing through `usage` so
  clients can chain `previous_response_id` follow-ups and observe
  `cached_tokens`. The follow-up request may reuse the public response `id`,
  but callers should not depend on the echoed `previous_response_id` string
  matching that public value byte-for-byte.
- `task-json` is an additional utility alias, not part of the public human
  chat-lane trio.
- `task-youtube-summary` follow-ups are retrieval-grounded through a durable
  `response_id -> document_id` mapping in the memory API rather than trusting
  provider conversation state alone.

## Configuration
- `config/router.yaml` maps logical handles to upstream endpoints.
- `config/env.example` provides the non-secret env template.
- `config/env.local` is git-ignored and remains the runtime env source for
  long-running service use.
- For Studio team lanes (`8100-8119`), use `platform/ops/scripts/mlxctl` and
  `mlxctl sync-gateway` as the source of truth flow.

## Verification
- `GET /v1/models` returns the expected logical handles from `config/router.yaml`
- `GET /health/readiness` is the default fast health signal
- `GET /health` is a deeper probe and may report unhealthy when backends are offline

## Supporting Docs
- `SERVICE_SPEC.md` for endpoint/auth/runtime details
- `RUNBOOK.md` for health checks and restart boundaries
- `CONSTRAINTS.md` for non-negotiables
- `docs/task-youtube-summary.md` for caller usage and operator architecture of
  the YouTube summary lane
