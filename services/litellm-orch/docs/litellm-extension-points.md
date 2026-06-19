# LiteLLM Extension Points (Proxy)

This doc is a quick map of LiteLLM proxy hooks and where we use them.

## 1) Callbacks / CustomLogger (callbacks)
Configured in `litellm_settings.callbacks` in `config/router.yaml`.

Use for:
- Pre-call request rewrites (e.g., persona expansion).
- Post-call response tweaks (non-stream).
- Logging/observability.

Key proxy-only hooks:
- `async_pre_call_hook` — modify requests before the LLM call.
- `async_post_call_success_hook` — modify responses after a successful call.

Other common logging hooks:
- `log_pre_api_call`, `log_post_api_call`
- `log_success_event`, `log_failure_event`
- async variants of the above.

## 2) Guardrails / CustomGuardrail
Configured in `guardrails:` in `config/router.yaml`.

Use for:
- Validation (accept/reject).
- Post-call sanitation/filters.
- Streaming response processing (iterator hook).

Supported event hooks (proxy):
- `async_pre_call_hook`
- `async_moderation_hook` (parallel to LLM call)
- `async_post_call_success_hook`
- `async_post_call_streaming_iterator_hook`

Mode controls which hook runs:
- `pre_call`, `during_call`, `post_call`.

## 3) Callback APIs (Enterprise)
LiteLLM supports sending standard logging payloads to external endpoints via
`success_callback` / `failure_callback` (Enterprise feature).

## Where we use these
- `config/responses_contract_guardrail.py` → `pre_call` / `post_call`
  Responses policy logging and deterministic task-alias normalization for
  `task-transcribe` and `task-json`.
- `config/llmster_toolcall_guardrail.py` → narrow `deep`, `fast`, and
  `code-reasoning` compatibility shim for non-streaming auto-tool requests
  where the llmster backend may leak raw tool protocol.
- `config/gpt_request_defaults.py` → narrow GPT-OSS request-default shim that
  injects omitted low reasoning effort for the current llmster lanes.
- `config/task_json_guardrail.py` → text-only transcript-to-JSON request
  shaping, schema injection, JSON normalization, and one repair attempt.

Historical prompt, Harmony, Qwen post-hook, and transcribe guardrails have been
retired from the active service tree. Reintroduce any similar behavior only
through a fresh router change, current provider evidence, and tests.

## Keep in mind
- Pre-call hooks can mutate requests; guardrails should enforce correctness.
- For streaming responses, use `async_post_call_streaming_iterator_hook`.
