# Decision Log

## 2026-01-03 — Gateway & Naming Decisions
- Chose LiteLLM proxy mode for the gateway (no custom FastAPI forwarder in Phase 1).
- Standardized OpenAI-compatible endpoints: `/v1/chat/completions` and `/v1/models`.
- Adopted plain client-facing model names (`jerry-*`, `lil-jerry`) to keep `/v1/models` clean; LiteLLM still uses `openai/<upstream>` in `litellm_params.model` for provider routing.

## 2026-01-03 — Backend Topology & Aider Roles
- MLX OpenAI servers run on the Studio at ports `8100`, `8101`, `8102`, `8103`; OpenVINO remains on the Mini at `9000`.
- `jerry-chat` (GPT-OSS) is pinned to port `8100` as the always-on Studio model; `jerry-weak` moved to `8103`.
- Aider uses three roles: architect (planning), editor (edits), weak (summaries/utility).

## 2026-01-03 — MLX Chat Template Issue
- Observed MLX server failures when `apply_chat_template` returns `BatchEncoding`.
- Applied a local patch in the Studio MLX server environment to coerce `BatchEncoding → input_ids`.
- Tracked a durable upstream fix as a “Nice to Have” (fork MLX server or upstream patch).
