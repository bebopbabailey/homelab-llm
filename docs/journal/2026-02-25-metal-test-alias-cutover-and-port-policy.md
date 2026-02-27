# 2026-02-25 — Metal-test alias cutover and port policy clarification

## Goal
Retire active `swap` alias usage and replace this experiment with temporary
`metal-test-*` aliases while clarifying Studio port governance.

## What changed
- LiteLLM experimental aliases were renamed:
  - `swap` -> `metal-test-fast`
  - `swap-main` -> `metal-test-main`
  - `swap-deep` -> `metal-test-deep`
- Active routing/env usage of `swap*` was removed from:
  - `layer-gateway/litellm-orch/config/router.yaml`
  - `layer-gateway/litellm-orch/config/env.local`
- Procedures/docs now state:
  - `8100-8119` are `mlxctl`-managed team lanes.
  - `8120-8139` are experimental lanes and do not require `mlxctl`.
- `metal-test-*` naming is explicitly documented as temporary for this
  experiment, not a permanent convention.

## Validation
- LiteLLM restarted successfully.
- `/v1/models` includes `metal-test-fast`, `metal-test-main`, `metal-test-deep`.
- Chat completions succeed for all three new aliases.
- Requests to deprecated `swap*` aliases fail as expected.

## Outcome
- Status: PASS (FAST)
- Outcome: swap naming is fully deprecated for active use; experimental canaries
  are now explicit and policy-aligned.
