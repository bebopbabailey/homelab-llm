# 2026-04-27 - GPT-OSS Responses follow-up contract

## Summary

Validated the remaining GPT-OSS Responses features that matter for the current
task-alias workflow and codified the resulting contract.

Result:
- keep `llmster` as the upstream owner of GPT-OSS Responses semantics
- treat direct raw `8126` assistant text as `output`-first, not
  `output_text`-first
- preserve `id`, `previous_response_id`, and `usage` through LiteLLM
- treat `task-transcribe-vivid` as the supported multi-turn transcript
  manipulation lane

## Runtime observations

- Host: Studio direct `llmster` on `192.168.1.72:8126`
- Direct `/v1/responses` returns:
  - stable response `id`
  - follow-up `previous_response_id`
  - `usage.input_tokens_details.cached_tokens`
  - separated reasoning in `output`
- Direct raw `output_text` is not a stable truth-path requirement. It can be
  `null` while the final assistant text is still present in the `output`
  message content.
- LiteLLM task aliases already improve ergonomics by exposing stable
  `output_text` while preserving `id`, `previous_response_id`, and `usage`.
  The caller can reuse the public response `id` successfully on a follow-up
  request, but the echoed `previous_response_id` in the resulting payload does
  not remain byte-for-byte equal to that public `id`.

## Validation evidence

Direct `8126` probes:
- one-shot Responses probe on `20b` returned:
  - `id`
  - `previous_response_id = null`
  - `usage.input_tokens_details.cached_tokens = 0`
- chained follow-up probe on `120b` returned:
  - second response `previous_response_id` matching the first `id`
  - `cached_tokens` field present on both responses
- structured Responses probe on `20b` succeeded when constrained to:
  - `temperature = 0.0`
  - `reasoning.effort = low`
  - `max_output_tokens = 256`
  - strict `text.format.type = json_schema`

LiteLLM probe:
- `task-transcribe-vivid` on `/v1/responses` returned:
  - stable gateway response `id`
  - stable `output_text`
  - `usage.input_tokens_details.cached_tokens = 624`

## Decision

- Do not add a new LiteLLM cache/state layer.
- Do not promise upstream `output_text` for raw `fast` / `deep`.
- Do document `previous_response_id` and `cached_tokens` as supported client
  features for the Responses-first GPT-OSS surface.
- Keep the direct GPT acceptance harness responsible for validating those
  fields on the raw backend.

## Cleanup state

- No backend topology change
- No `llama-server` cutover
- No new LiteLLM gateway mutation beyond contract/test/doc codification
