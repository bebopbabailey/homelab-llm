# 2026-03-18 — GPT `deep` canary contract + shared-posture proof

## Summary
- Added a temporary non-public Mini-side `deep-canary` alias contract for the
  future `deep` llmster backend path.
- Tightened the GPT rollout evidence order so raw standalone refresh stays
  separate from the LM Studio daemon/runtime refresh.
- Made actual post-load shared-posture proof explicit before any public `deep`
  cutover on shared `8126`.

## Why
The repo already had a usable-success gate for `deep`, but it still needed two
operational hardening details:
- a safer Mini-side gateway proof step before repointing canonical public `deep`
- proof of real dual-load residency and memory posture, not just
  `lms load --estimate-only`

## Contract changes
- `deep-canary` is now the approved temporary non-public LiteLLM alias for the
  future `deep` llmster target.
- Shared `8126` remains the default first attempt for `deep`, but public
  cutover now requires:
  - `estimate-only` pass
  - actual dual-load idle posture proof
  - `fast` regression rerun under the actual loaded posture
- Stable residency for canonical GPT lanes is now explicit and must be proven
  with:
  - `lms ps --json`
  - `/v1/models`

## Notes
- This change does not make `deep` live.
- `/v1/responses` remains advisory for the current GPT hardening phase.
- If `deep` ultimately passes because constrained tool mode is strong while
  `auto` is only usable, the final codified lane contract must say so plainly.
