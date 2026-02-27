# 2026-02-22 — OptiLLM MLX `server.diff` rebase and strict GO

## Context
The strict main-lane campaign on 2026-02-21 was stable `NO_GO` because
maintainability failed (`server.diff` no longer applied to upstream `mlx-lm`).

This entry records the rebase fix and the strict re-validation run.

## Change performed
- Rebased patch file:
  - `layer-inference/optillm-local/runtime/patches/mlx_lm/server.diff`
- Rebase method:
  - cloned current upstream `ml-explore/mlx-lm`
  - applied existing patch with rejects
  - resolved the single rejected hunk in batch insert path
  - regenerated `server.diff` from upstream working tree

## Maintainability verification
- Upstream commit checked:
  - `321e764e0ab6dfa80d52a478f75d453313e00c9a`
- Command result:
  - `git apply --check layer-inference/optillm-local/runtime/patches/mlx_lm/server.diff`
  - result: pass

## Runtime strict campaign (after rebase)
- Preflight:
  - `ssh studio "mlxctl status --checks"` confirmed 8130 listening (`mlx_lm.server`)
  - tunnel used: Mini `127.0.0.1:18130` -> Studio `127.0.0.1:8130`
- Campaign command:
  - `uv run python layer-inference/optillm-local/scripts/run_viability_campaign.py --gate-config /tmp/optillm_mlx_main_strict_rebased.json --runs 3 --print-run-logs`

## Outcome
- Campaign summary:
  - `/tmp/optillm_mlx_campaign_20260222-001410/campaign_summary.json`
- Stable decision:
  - `GO` (`3/3`)
- Per-run strict reports:
  - `/tmp/optillm_mlx_campaign_20260222-001410/run_01/optillm_mlx_viability_20260222-001410/viability_report.json`
  - `/tmp/optillm_mlx_campaign_20260222-001410/run_02/optillm_mlx_viability_20260222-001442/viability_report.json`
  - `/tmp/optillm_mlx_campaign_20260222-001410/run_03/optillm_mlx_viability_20260222-001515/viability_report.json`

## Key interpretation
- Main-lane entropy path is now passing strict gates including:
  - model/runtime gate
  - quality gate
  - maintainability gate
- The prior strict `NO_GO` was resolved by patch rebase (not by loosening gates).

## Next step
- Add secondary validation lane (`gpt-oss-20b`) back into strict campaign to
  confirm results generalize beyond the main Qwen lane.
