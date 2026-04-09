# 2026-03-18 — `main` closeout and GPT-lane transition

## Summary
- `main` on Studio `8101` is closed as an active backend project.
- `main` remains the accepted public canary lane with known limitations.
- Structured outputs remain outside the accepted public `main` contract on the current runtime.
- Forced-tool semantics remain unsupported and non-blocking on the current runtime.
- Legacy `8123|8124|8125` `main`/helper shadow and fallback concepts are preserved only as dormant recovery metadata.
- Active backend work shifts fully to GPT-family `llmster` rollout and hardening for `fast` and `deep`.

## Final accepted `main` contract
- Non-stream `tool_choice="auto"` is accepted.
- Long-context sanity is accepted.
- Bounded concurrency is accepted.
- Branch-style concurrency and suitability are accepted.

## Accepted limitations
- Structured outputs are outside the accepted public `main` contract on the current runtime.
- `tool_choice="required"` is unsupported and non-blocking.
- Named forced-tool choice is unsupported and non-blocking.

## Recovery posture
- `8123|8124|8125` remain approved dormant recovery space for legacy `main`/helper rollout concepts.
- Those ports are no longer part of active rollout language, current-work narratives, or public alias expectations.
- Historical reports and journals remain the source record for the earlier `main` shadow/fallback exploration.

## Evidence chain
- [2026-03-18-qwen-main-acceptance-codified-with-posthook.md](2026-03-18-qwen-main-acceptance-codified-with-posthook.md)
- [2026-03-18-main-8101-structured-output-protocol-validation.md](2026-03-18-main-8101-structured-output-protocol-validation.md)
- retired root-level validation report reference; see
  `docs/_core/consistency_audit_2026-04.md`

## Active work after closeout
- `fast` remains the live GPT-family `llmster` lane on `8126`.
- `deep` is the next GPT-family rollout target.
- Any future `main` backend work would require a new explicitly named backend-specific project.
