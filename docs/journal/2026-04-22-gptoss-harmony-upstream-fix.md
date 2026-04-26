# 2026-04-22 - GPT-OSS Harmony upstream-fix validation

## Summary

The GPT-OSS follow-up was moved back to the boring supported path: validate the
shared `llmster` runtime directly first, then keep only the LiteLLM shims still
required by defects that reproduce on direct `8126`.

Result:
- **do not add a general LiteLLM Harmony formatter/stripper for GPT lanes**
- keep one narrow `reasoning_effort=low` pre-call shim because omitted-effort
  direct GPT-OSS chat requests can still leak raw Harmony protocol or truncate
  final content
- drop the `task-transcribe` fast->deep retry because the direct `fast` truth
  path now returns usable assistant content for the standard transcribe prompt

## Runtime posture observed

- Host: Studio.
- Service: `llmster` / LM Studio server on port `8126`.
- LM Studio / `llmster` launcher path:
  `/Users/thestudio/.lmstudio/llmster/0.0.7-4/.bundle/lms`
- observed CLI commit: `f26090f`
- loaded GPT identifiers:
  - `llmster-gpt-oss-20b-mxfp4-gguf`
  - `llmster-gpt-oss-120b-mxfp4-gguf`
- observed native load config on `GET /api/v1/models`:
  - `context_length=32768`
  - `eval_batch_size=512`
  - `flash_attention=true`
  - `num_experts=4`
  - `offload_kv_cache_to_gpu=true`
  - `parallel=4` for 20B and `parallel=2` for 120B

## Validation results

Direct shared `8126` truth-path:
- `POST /v1/chat/completions` with `reasoning_effort=low` returns:
  - visible answer text in `choices[0].message.content`
  - separated reasoning in `choices[0].message.reasoning`
- `POST /v1/responses` returns:
  - reasoning items in the `output` array
  - final answer text in `output_text` / output message content
- `response_format.type=json_schema` succeeds on the current LM Studio path
- direct `deep` auto-tool response returned valid `tool_calls` without raw
  protocol text

Direct shared `8126` defect still present:
- `fast` Chat Completions without explicit `reasoning_effort` can still return
  raw Harmony protocol such as `<|channel|>` instead of final answer text on
  short probes

## Code changes

- The GPT-OSS acceptance harness now treats raw Harmony marker leakage as a
  first-class failure signal and records snippets under `raw_harmony_leaks`.
- The `llmster_ensure_server.py` bootstrap now:
  - skips reloads when the identifier is already loaded with the expected
    config
  - validates native `GET /api/v1/models` load posture
  - unloads/reloads when identifier config drifts
- `task-transcribe` no longer keeps a Mini-side retry onto `deep`; the direct
  `fast` truth-path now produces valid content for the standard transcribe
  prompt, so only the narrow transcript cleanup/sanitizing path remains

## Interpretation

The current supported shape is:
- upstream `llmster` is the formatting owner for GPT-OSS on `8126`
- `/v1/responses` and `message.reasoning` are now real upstream surfaces in the
  deployed runtime and should be treated as such in repo canon
- LiteLLM should keep only defect-specific shims proven necessary directly
  upstream

## Recommendation

Keep `gpt-request-defaults` for omitted `reasoning_effort` on GPT-OSS chat
lanes. Do not add a broader Harmony post-call formatter for `fast`/`deep`.

Keep `task-transcribe` on `fast` and `task-transcribe-vivid` on `deep`, but
build them on top of the corrected upstream contract rather than a backend
retry shim.
