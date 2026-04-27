# NOW

Active
- Move the public GPT-OSS LiteLLM surface (`fast`, `deep`, `task-*`) to a
  Responses-first contract on top of the corrected shared `llmster` backend,
  then codify the direct `8126` follow-up/cached-token contract and the client
  usage pattern for `task-transcribe-vivid`.

NEXT UP
- Start using `previous_response_id` in client follow-up flows and observe
  `usage.input_tokens_details.cached_tokens` before considering any deeper
  backend/runtime tuning.
