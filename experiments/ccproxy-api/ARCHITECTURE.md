# Architecture: ccproxy-api

## Role
- Provide a localhost-only Codex-backed OpenAI-compatible API surface on the
  Mini using upstream CCProxy.
- Normalize the Codex subscription backend into a clean Chat Completions path
  that LiteLLM and Open WebUI can consume.

## Data Flow
- Open WebUI -> LiteLLM -> `ccproxy-api` -> OpenAI Codex backend.
- Direct operator validation may call `http://127.0.0.1:4010/codex/v1/*`.

## Boundaries
- LiteLLM remains the single user-facing gateway.
- `ccproxy-api` is experimental and scoped to the `chatgpt-5` alias only.
