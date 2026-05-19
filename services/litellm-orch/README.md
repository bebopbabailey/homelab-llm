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
- `task-transcribe` uses one dotprompt-backed cleanup lane; optional
  `prompt_variables.audience` / `prompt_variables.tone` subtly shape rhythm
  and audience fit
- `task-youtube-transcript` is a YouTube transcript acquisition alias routed to
  the Mini-local `youtube-transcript-api`
- Voice Gateway on the Orin for STT aliases
- SearXNG on the Mini for generic search tooling

## OpenCode Note
- Repo-local OpenCode defaults and agent/skill behavior are documented in
  `/home/christopherbailey/homelab-llm/docs/OPENCODE.md`.
- The local canonical public human lanes remain `fast` and `deep`.
- Public GPT-OSS traffic is Responses-first through LiteLLM for `fast`,
  `deep`, `task-transcribe`, and `task-json`.
- `POST /v1/chat/completions` remains a temporary compatibility path for the
  GPT-OSS public aliases during the current migration window.
- `chatgpt-5` keeps its own adapter-backed dual-endpoint behavior.
- `chatgpt-5` now routes through the Mini-local `ccproxy-api` Codex sidecar.
- `task-transcribe` is an additional task alias, not part of the public human
  chat-lane trio.
- Its prompt is registered in LiteLLM's native dotprompt config and rendered
  from `prompt_id` / `prompt_variables`; the transcribe guardrail preserves
  transcript punctuation, supplies prompt variables, routes direct audio
  uploads through STT, and strips wrapper fields from the final response
  payload.
- Direct file-upload callers may also use `POST /v1/audio/transcriptions` with
  `model=task-transcribe`; LiteLLM first routes audio to `voice-stt`, then
  cleans the raw transcript and returns `id` plus `output_text`. Add
  `prompt_variables.audience` / `prompt_variables.tone` for subtle shaping.
- `task-youtube-transcript` is also an additional task alias, not part of the
  public human chat-lane trio. It routes normal Chat Completions requests to
  the localhost-only `youtube-transcript-api` service on `127.0.0.1:8014/v1`;
  the assistant message content is plain timestamped transcript text.
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
