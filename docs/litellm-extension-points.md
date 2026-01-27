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
- `config/persona_router.py` → CustomLogger pre-call rewrites (personas).
- `config/transcribe_guardrail.py` → post-call wrapper stripping (transcribe).
- `config/strip_reasoning_guardrail.py` → remove reasoning content for select aliases.
- `config/promptopt_guardrail.py` → post-call fan-out reducer (p-opt-max).

## Keep in mind
- Pre-call hooks can mutate requests; guardrails should enforce correctness.
- For streaming responses, use `async_post_call_streaming_iterator_hook`.
