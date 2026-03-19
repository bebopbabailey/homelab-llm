# 2026-03-18 — GPT `llmster` fast-observation + deep usable-success contract

## Summary
This pass tightened the GPT-family rollout contract around the existing
`llmster` / llama.cpp path without redesigning the stack.

`fast` remains live on Studio `8126`, but the repo canon now treats it as
canary-canonical while the LM Studio daemon/runtime refresh and `deep` rollout
are still open. `deep` remains the next rollout target.

## What changed
- widened the GPT acceptance harness to cover:
  - structured nested output
  - `tool_choice="required"`
  - named-tool forcing
  - `/v1/responses` smoke
  - clean arg-bearing probes versus large-schema stress as separate cases
- added a thin daemon-aware LM Studio wrapper script for `8126`
- updated the `8126` plist template to pin a versioned `lms` binary path and
  bootstrap through the thin wrapper instead of calling the moving shim
  directly
- updated the canonical docs to say:
  - raw standalone llama.cpp is diagnostic-first, not the public promotion
    oracle by itself
  - GPT lanes are Chat Completions-first in the current hardening phase
  - `/v1/responses` is advisory unless it exposes a defect that also matters to
    the public Chat Completions lane
  - `deep` is promotable once it is operationally useful, not perfect

## Deep usable-success gate
- plain chat clean
- structured simple clean
- structured nested clean
- auto noop strong
- auto arg-bearing usable at `>= 8/10` on direct `llmster` and public LiteLLM
- at least one constrained mode strong:
  - `tool_choice="required" >= 9/10`, or
  - named-tool forcing `>= 9/10`
- crashes, listener loss, sustained readiness regressions, repeated `5xx`, and
  repeated timeouts remain blockers

## Raw mirror policy
Raw standalone `llama-server` remains valuable for:
- truth-path debugging
- parser/runtime comparison
- tuning
- regression diagnosis

But raw divergence alone does not block GPT lane promotion unless it reveals a
crash, gross corruption, or a reproducible defect that also appears on direct
`llmster` or the public LiteLLM lane.

## Follow-on work
- close the `fast` observation window
- refresh the LM Studio daemon/runtime through supported `lms` commands
- revalidate `fast`
- stage `deep`
- prove shared `8126` posture with `lms load --estimate-only`
- fall back to a separate public `8127` only if shared fit is not viable
