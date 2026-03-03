# 2026-03-01 — Studio per-lane launchd recovery + OOM guardrails

## What changed
- Implemented per-lane launchd orchestration in `mlxctl` for team lanes.
  - `mlxctl mlx-launch-start` now materializes and starts:
    - `com.bebop.mlx-lane.8100`
    - `com.bebop.mlx-lane.8101`
    - `com.bebop.mlx-lane.8102`
  - Each lane uses `KeepAlive=true` and `ThrottleInterval=30` for lane-local auto-restart.
  - Legacy `com.bebop.mlx-launch` is disabled/booted out during `mlx-launch-start`.
- `mlxctl mlx-launch-stop` now stops/disables per-lane labels and legacy label, then clears managed listeners.
- Added conservative vLLM memory defaults when registry values are missing:
  - `gpt-oss-120b`: `0.55`
  - `qwen3-next-80b`: `0.50`
  - `gpt-oss-20b`: `0.45`
- `mlx-launch-start` now persists missing runtime defaults into Studio registry entries:
  - `vllm_max_model_len`
  - `vllm_memory_fraction`
  - `vllm_async_scheduling=false`

## Policy + docs alignment
- Updated Studio scheduling policy manifest to managed per-lane labels and retired `com.bebop.mlx-launch`.
- Updated canonical topology/dossier/registry/runbook/testing docs to reflect per-lane launchd ownership and active `8100/8101/8102` lanes.

## Why
- Incident root cause: `8102` process died on Metal OOM and stayed down because old single launcher had no per-lane respawn path.
- New design reduces blast radius and enables lane-local restart after crash.

## Validation run (repo-side)
- `python3 -m py_compile platform/ops/scripts/mlxctl` ✅
- `uv run python platform/ops/scripts/validate_studio_policy.py --json` ✅
- `uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json` ✅
- `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --json` ❌
- `uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json` ❌
- `./platform/ops/scripts/mlxctl status` ⚠️ (`8102` idle)
- `./platform/ops/scripts/mlxctl verify` ❌ (`8102` assigned but not listening)

## Notes on failed remote checks
Remote policy/audit failures are expected before applying the new launchd state on Studio:
- new managed labels are not installed yet (`com.bebop.mlx-lane.8100/.8101/.8102`)
- retired label still loaded (`com.bebop.mlx-launch`)
- existing runtime still under `/opt/mlx-launch/bin/start.sh`

## Next operational step
Apply on Studio in staged order:
1. `./platform/ops/scripts/mlxctl mlx-launch-stop --ports 8100,8101,8102`
2. `./platform/ops/scripts/mlxctl mlx-launch-start`
3. Re-run strict policy/audit + `mlxctl status` + `mlxctl verify`.
