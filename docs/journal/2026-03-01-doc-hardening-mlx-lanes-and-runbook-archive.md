# 2026-03-01 — Doc hardening for MLX lane canon + 812x archive split

## Why
Root and foundation docs were aligned to the per-lane `vllm-metal` reality (`8100/8101/8102`),
but two ambiguity points remained:
- `docs/foundation/testing.md` implied `8100` was the only required listener check.
- `layer-inference/RUNBOOK.md` mixed canonical operations with historical `8120/8121/8122`
  experimental procedures.

## What changed
1. Canonical runbook deconfliction:
   - `layer-inference/RUNBOOK.md` now keeps active operational guidance only.
   - Historical `812x` tuning/forensics content moved to:
     `docs/archive/2026-03-layer-inference-812x-experimental-tuning-history.md`.
   - Runbook includes explicit archive link and statement that `812x` content is historical.

2. Dynamic active-lane verification:
   - `docs/foundation/testing.md` now checks all active lanes from
     `mlxctl status --json` instead of treating `8101/8102` as optional.
   - Added date-bound expectation: as of `2026-03-01`, production active lanes are
     `8100/8101/8102`; deviations are drift.

## Resulting runtime contract for agents
- Production MLX lane operations: `layer-inference/RUNBOOK.md`
- Model-to-port truth: `docs/foundation/mlx-registry.md`
- Studio launchd policy truth: `docs/foundation/studio-scheduling-policy.md`
- Historical `812x` experimentation: archive doc only

## Verification run
- `rg` checks confirmed stale `8100-only`/`optional 8101-8102` language removed.
- `mlxctl status --json` dynamic extraction works in current runtime.
- `mlxctl verify` returns `ok`.
