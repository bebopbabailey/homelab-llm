# 2026-03-18 — OpenHands Phase B delay under three-alias backend hardening

## Summary
- OpenHands Phase B is intentionally delayed while backend hardening focuses on
  the canonical public LLM aliases `fast`, `main`, and `deep`.
- `code-reasoning` is removed from the active gateway contract in this phase.

## Operational implication
- There is no active OpenHands-specific LiteLLM alias during this hardening
  window.
- Future OpenHands model selection and worker policy should be revisited only
  after the backend-hardening program finishes the public `main` cutover and the
  later GPT-family tuning work.
