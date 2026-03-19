# 2026-03-18 — Canonical `8101` Qwen main cutover + three-alias gateway surface

## Summary
- Canonical `main` is promoted onto Studio team lane `8101` using `mlxctl`.
- The active LLM alias surface is reduced to `fast`, `main`, and `deep`.
- `code-reasoning`, `helper`, `boost*`, rollout shadows, and `metal-test-*`
  are removed from the active gateway LLM contract.
- Voice and task aliases are removed from the active LiteLLM model surface in
  the same gateway reduction.

## Locked runtime interpretation
- Public `main` is `mlx-qwen3-next-80b-mxfp4-a3b-instruct` on Studio `8101`.
- Public `main` acceptance is:
  - structured outputs
  - long-context sanity
  - bounded generic concurrency
  - shared-prefix branch-style behavior
- Parsed `tool_calls` on `tool_choice="auto"` remain unreliable on the current
  canonical `8101` `vllm-metal` build: the lane still emits raw
  `<tool_call>...</tool_call>` markup instead of populated `tool_calls`.
- Forced-tool semantics remain unsupported on the current `vllm-metal` build.

## Implemented result
- Studio `8101` now serves `mlx-qwen3-next-80b-mxfp4-a3b-instruct` via
  `mlxctl` with:
  - `--max-model-len 32768`
  - `--generation-config vllm`
  - `--no-async-scheduling`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser hermes`
  - no explicit `--chat-template`
  - `VLLM_METAL_MEMORY_FRACTION=auto`
- LiteLLM `/v1/models` now exposes exactly:
  - `deep`
  - `fast`
  - `main`
- LiteLLM readiness is healthy after the gateway reduction.
- Public `main` through LiteLLM proves structured outputs.
- Public `fast` and `deep` remain functional on their current public GPT lanes.

## Rollback target
- `mlx-community/Llama-3.3-70B-Instruct-4bit` remains the last-known-good
  rollback target for `8101`.

## Gateway contract
- Active public LLM aliases:
  - `fast`
  - `main`
  - `deep`
- Removed from the active model surface:
  - `code-reasoning`
  - `helper`
  - `boost*`
  - `main-shadow`
  - `main-fallback-shadow`
  - `helper-shadow`
  - `fast-shadow`
  - `deep-shadow`
  - `metal-test-*`
  - `voice-*`
  - `task-transcribe*`

## Follow-on
- Future GPT-family tuning work continues directly on experimental Studio
  `8126`, but public `fast` and `deep` stay on their current lanes until that
  later evidence exists.
