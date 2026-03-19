# 2026-03-18 — Qwen auto-tool `8123` vs `8101` revalidation collapse

## Summary
- Re-ran the planned side-by-side direct backend check for Qwen3-Next on:
  - experimental `8123`
  - canonical `8101`
- Both lanes were on the same corrected contract family:
  - `--max-model-len 32768`
  - `--generation-config vllm`
  - `--no-async-scheduling`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser hermes`
  - no explicit `--chat-template`
- Structured outputs still passed on both lanes.
- Parsed `tool_calls` for `tool_choice="auto"` failed on both lanes.

## Direct comparison result
### `8123`
- structured outputs: PASS (`2/2`)
- `tool_choice="auto"`: FAIL (`0/10`)
- failure shape:
  - assistant `content` contains raw `<tool_call>...</tool_call>`
  - `tool_calls` is empty

### `8101`
- structured outputs: PASS (`2/2`)
- `tool_choice="auto"`: FAIL (`0/10`)
- failure shape:
  - assistant `content` contains raw `<tool_call>...</tool_call>`
  - `tool_calls` is empty

## Interpretation
- The earlier `8123` success no longer reproduces.
- There is no longer a meaningful `8123` vs `8101` delta for parsed
  `tool_choice="auto"` behavior.
- The current problem should now be treated as non-durable runtime drift or a
  broader runtime/parser behavior issue on the present `vllm-metal` build, not
  a canonical managed-lane-only defect.

## What this rules out
- The remaining problem is not explained by the old `8101` control-plane drift.
- The remaining problem is not explained by canonical-lane-only launch context.
- Chasing `8101`-specific lane differences is no longer the right next step.

## Current live state
- Canonical `main` remains Qwen on Studio `8101`.
- Active LiteLLM LLM aliases remain exactly:
  - `main`
  - `fast`
  - `deep`
- LiteLLM readiness remains healthy.
- `main` structured outputs continue to work.

## Next step
- Treat parsed `tool_calls` on Qwen `tool_choice="auto"` as a current
  vLLM-runtime problem on both `8123` and `8101`.
- Future debugging should focus on:
  - upstream/runtime behavior
  - parser behavior
  - model-output compatibility with the current `hermes` extraction path
- Do not spend more time on canonical `8101` vs shadow `8123` comparison until
  a new runtime change gives reason to expect divergence again.
