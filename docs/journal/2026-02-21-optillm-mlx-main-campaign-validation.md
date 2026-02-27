# 2026-02-21 — OptiLLM MLX main-lane campaign validation

## Context
Executed the next-step viability loop against the live Studio isolated endpoint
for entropy decoding (`mlx_lm.server` patch path), focused on the Qwen main lane.

## Host and endpoint
- Orchestration host: Mini
- Runtime target: Studio
- Target endpoint: Studio `127.0.0.1:8130` via Mini tunnel `127.0.0.1:18130`

## Preflight checks
- `ssh studio "mlxctl status --checks"` confirmed:
  - `8100/8101/8102` listening as expected
  - `8130` listening with runtime family `mlx_lm.server`
- `ssh studio "curl http://127.0.0.1:8130/v1/models"` confirmed model list
- Direct probe through tunnel returned valid completion (`"OK"`) on target Qwen model id

## Campaign A (main lane, quick-screen profile, no quality required)
Config:
- model set to Qwen3-Next-80B-A3B-Instruct-4bit snapshot id
- required_models: same single model
- concurrency: `1,4`
- repeats: `1`
- quality.required: `false`
- maintainability check: `false`

Command:
- `uv run python layer-inference/optillm-local/scripts/run_viability_campaign.py --gate-config /tmp/optillm_mlx_main_quick.json --runs 3 --print-run-logs`

Result:
- Campaign summary: `/tmp/optillm_mlx_campaign_20260221-032317/campaign_summary.json`
- Overall: `CONDITIONAL_GO`
- Stability: `3/3 CONDITIONAL_GO`
- Reason pattern: model/runtime gates passed; quality skipped; maintainability unverified

## Campaign B (main lane, quality required, maintainability enabled)
Config:
- same main-lane single-model setup
- quality.required: `true` with report `/tmp/optillm_mlx_quality_report.json` (status `pass`)
- maintainability check: `true`

Command:
- `uv run python layer-inference/optillm-local/scripts/run_viability_campaign.py --gate-config /tmp/optillm_mlx_main_strict.json --runs 3 --print-run-logs`

Result:
- Campaign summary: `/tmp/optillm_mlx_campaign_20260221-032530/campaign_summary.json`
- Overall: `NO_GO`
- Stability: `3/3 NO_GO`
- Per-run reports:
  - `/tmp/optillm_mlx_campaign_20260221-032530/run_01/optillm_mlx_viability_20260221-032530/viability_report.json`
  - `/tmp/optillm_mlx_campaign_20260221-032530/run_02/optillm_mlx_viability_20260221-032604/viability_report.json`
  - `/tmp/optillm_mlx_campaign_20260221-032530/run_03/optillm_mlx_viability_20260221-032636/viability_report.json`

Key finding:
- Runtime/quality on main lane passed.
- Final `NO_GO` was driven by maintainability only:
  - `server.diff does not apply cleanly to upstream`
  - `error: patch failed: mlx_lm/server.py:758`

## Interpretation
- Entropy approach appears operational and performant enough on main lane under
  this profile.
- Current blocker is patch drift against upstream, not immediate runtime quality.

## Next step
- Rebase/refresh `layer-inference/optillm-local/runtime/patches/mlx_lm/server.diff`
  to current upstream `mlx-lm`, then re-run Campaign B unchanged.
