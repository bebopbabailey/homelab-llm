# 2026-03-20 — GPT formatting ownership pushed upstream

## Summary
- Re-ran the direct truth-path sweep for `main` on `8101` and `fast` / `deep`
  on shared `8126`.
- Confirmed the accepted direct backends are already producing clean
  client-visible formatting and structured tool-call shapes for the supported
  contract.
- Narrowed LiteLLM from canonical GPT formatter to one small request-default
  shim for omitted `reasoning_effort=low` on `fast`, `deep`, and internal
  worker alias `code-reasoning`.

## Findings
- Direct `8101` on the locked `hermes` parser returned clean plain-chat content
  and structured `tool_calls` for non-stream `tool_choice="auto"` probes.
- Direct shared `8126` returned clean content and structured `tool_calls`
  without raw Harmony wire-tag leakage.
- Current `llmster` server/loader controls do not expose a server-side default
  knob for `reasoning_effort`.
- Named/object-form forced-tool choice remains unsupported on the current GPT
  backend family.
- One strict schema probe can succeed, but strict structured-output guarantees
  are still out of contract.

## Decision
- Upstream owns GPT formatting/tool-call parsing for:
  - `main`
  - `fast`
  - `deep`
  - internal OpenHands worker alias `code-reasoning` by inheritance from `deep`
- LiteLLM keeps only:
  - auth
  - routing
  - fallbacks
  - observability
  - GPT request-default injection of `reasoning_effort=low` when omitted for
    `fast`, `deep`, and `code-reasoning`

## What changed
- Removed active GPT Harmony pre/post response rewriting from the LiteLLM
  router.
- Removed the active Qwen `main` post-call cleanup hook from the LiteLLM router.
- Added a tiny `gpt_request_defaults` pre-call guardrail to keep omitted
  `reasoning_effort=low` behavior until the current `llmster` service contract
  can own that upstream.
- Updated canonical docs to stop treating LiteLLM as the GPT formatting owner.
