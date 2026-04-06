# 2026-04-02 — Homelab durability evaluation loop after hygiene hardening

## Summary
- Re-ran the durability workflow against the stronger root/journal/archive
  contracts and the new control-plane sync audit.
- The stage split still held: `Discover` and `Design` stayed light, while
  `Build` and `Verify` remained strict around writes, host awareness, and
  rollback-gated runtime actions.
- One repo-local improvement was worth codifying: when root-entry hygiene is the
  task, the machine-checked manifest should outrank ad hoc memory.

## What held up
- Conditional startup declaration remained the right tradeoff for discovery and
  planning.
- Conditional rollback remained the right tradeoff for docs-only and read-only
  work.
- Dirty-tree caution in `Build` and `Verify` still matched the repo’s actual
  failure modes.

## Adjustment made
- Added an explicit source-of-truth pointer to
  `docs/_core/root_hygiene_manifest.json` when changing root/journal/archive
  placement rules.
- Added an explicit reminder that repo-entry hygiene should follow the
  validator-backed manifest rather than prose memory.

## Outcome
- No broader rewrite of `homelab-durability` was necessary after the hygiene
  pass.
- The next meaningful loop should happen only if journal/archive enforcement is
  promoted from advisory to hard-fail or if control-plane sync rules expand.
