# 2026-03-19 — Public `deep` cutover to shared `8126`

## Summary
- Repointed canonical public `deep` from MLX `8100` to the shared Studio
  `llmster` listener on `192.168.1.72:8126`.
- Kept LiteLLM on the Mini as the public control plane.
- Preserved raw standalone `llama-server` mirrors as diagnostic-first seams on
  Studio loopback.
- Kept `deep-canary` temporarily after cutover for brief operator comparison.

## Pre-cutover evidence
- Closed the `fast` observation window on the current live LM Studio stack.
- Refreshed raw standalone llama.cpp to a versioned `b8416` build while leaving
  the live `llmster` stack untouched.
- Checked LM Studio through supported commands; current daemon remained
  `v0.0.7+4` and current selected GGUF runtime remained
  `llama.cpp-mac-arm64-apple-metal-advsimd@2.7.1`.
- Imported `gpt-oss-120b` MXFP4 GGUF into LM Studio.
- `lms load --estimate-only` showed the shared `8126` posture well below the
  current planning ceiling.
- Actual shared-posture proof passed:
  - both models visible in `lms ps --json`
  - both models visible in `/v1/models`
  - idle memory snapshots stable across a 5-minute interval
  - `fast` still healthy under the dual-load posture

## Validation order
1. Raw deep on loopback `8131`
2. Direct `llmster` deep on `8126`
3. Mini-side non-public `deep-canary`
4. Canonical public `deep`

## Public `deep` result
- `plain_chat`: `5/5`
- `structured_simple`: `5/5`
- `structured_nested`: `5/5`
- `auto_tool_noop`: `10/10`
- `auto_tool_arg`: `10/10`
- `required_tool_arg`: `9/10`
- `named_tool_arg`: unsupported on the current backend path, returning
  backend-visible `400` for object-form `tool_choice`
- `responses_smoke`: passed and remains advisory
- `concurrency_smoke`: passed with `200` on all requests in the cutover run

## Locked contract after cutover
- Public GPT lanes remain Chat Completions-first.
- `fast` remains canary-canonical on shared `8126`.
- Public `deep` is accepted on shared `8126` under a usable-success contract.
- `required` is the locked strong constrained-tool path for public `deep`.
- Named forced-tool choice is unsupported and non-blocking on the current
  `llmster` / llama.cpp GPT backend.
- `deep-canary` is temporary and should be retired after a short observation
  period.

## Follow-up
- Observe the shared `8126` dual-load posture.
- Retire `deep-canary` after the observation window if no comparison need
  remains.
