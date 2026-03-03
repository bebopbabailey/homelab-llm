# 2026-03-03 — mlxctl lane repair + launchd drift hardening

## Summary
Implemented durability hardening in `mlxctl` for Studio team lanes (`8100-8119`) to surface and remediate launchd drift that caused brittle lane recovery.

## Changes
- Added launchd drift visibility in `mlxctl status --checks`:
  - `launchd_label`
  - `launchd_loaded`
  - `launchd_disabled`
- Strengthened `mlxctl verify` to fail when an assigned team-lane label is:
  - disabled, or
  - not loaded.
- Added `mlxctl repair-lanes`:
  - dry-run by default
  - `--apply` enables and bootstraps assigned team-lane labels
  - optional `--ports` scope (team lanes only)
- Added guardrail to `mlxctl mlx-launch-start --ports`:
  - refuses partial assigned-team-lane scope by default
  - explicit override via `--allow-partial`.

## Why
Recent failures included assigned lanes that were down because launchd labels were disabled/unloaded. Previous checks could pass process-level signals without clearly surfacing launchd-state drift. This patch makes drift explicit and repairable through one canonical command.

## Validation
- Unit tests: `uv run python platform/ops/scripts/tests/test_mlxctl_vllm_flags.py`
- New coverage includes:
  - launchctl `print-disabled` parser
  - mutating classification for `repair-lanes` apply mode.

## Operational Result (same day)
- `repair-lanes --json` identified `8100` (`com.bebop.mlx-lane.8100`) as disabled/unloaded and down.
- `repair-lanes --apply --json` repaired the assigned lane label.
- `mlxctl status --checks --json` after apply:
  - `8100/8101/8102` all report `runtime_family=vllm-metal`
  - all three assigned labels report `launchd_loaded=true`, `launchd_disabled=false`
- `mlxctl verify` passed with no drift findings.
- Direct Studio lane probes passed:
  - `8100` -> `mlx-gpt-oss-120b-mxfp4-q4`
  - `8101` -> `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
  - `8102` -> `mlx-gpt-oss-20b-mxfp4-q4`
