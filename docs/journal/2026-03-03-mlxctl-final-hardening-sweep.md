# 2026-03-03 — mlxctl final hardening sweep (safe/no-UX-change)

## Summary
Completed a final durability sweep for `mlxctl` with a conservative posture: no command-surface regressions, no port-policy changes, and no new exposure. The sweep focused on clearer health truth signals, safer argument parsing, stronger off-Studio repair behavior, and better failure diagnostics.

## Changes
- Added shared parsing helpers:
  - `_parse_int_arg`
  - `_parse_port_arg`
  - `_parse_port_csv`
- Added shared JSON parser helper:
  - `_loads_json_or_die` (path/context-aware decode errors)
- `status --checks` now emits `http_models_ok` per non-idle lane.
- `repair-lanes` hardened for Mini orchestration:
  - excluded from auto-forward list (same orchestration class as `mlx-launch-*`)
  - fetches registry/status from Studio when run off-Studio
  - evaluates lane-down using `listener/process/http` truth set
  - uses Studio sudo wrapper path for launchctl apply steps
  - records per-step apply diagnostics in JSON payload (`apply_result.steps`)
- Hardened vLLM capability probe:
  - timeout support via `MLX_VLLM_HELP_TIMEOUT_SECONDS`
  - fail-closed on unusable help output
- Applied safer integer/port parsing in key command paths (`load/unload`, `omni-*`, `mlx-launch-*`, team-port resolvers).

## Verification
- Local checks:
  - `uv run python -m py_compile platform/ops/scripts/mlxctl`
  - `uv run python platform/ops/scripts/tests/test_mlxctl_vllm_flags.py` (10 tests pass)
  - `uv run python platform/ops/scripts/tests/test_mlxctl_runtime_health.py` (2 tests pass)
- Studio parity + runtime:
  - `mlxctl sync-studio-cli` + `mlxctl studio-cli-sha` (match=true)
  - `mlxctl status --checks --json`:
    - `8100/8101/8102` => `status=running`, `runtime_family=vllm-metal`, `http_models_ok=true`, `launchd_loaded=true`, `launchd_disabled=false`
  - `mlxctl verify` passed
  - `mlxctl repair-lanes --json` => `repair_count=0`
  - `mlxctl mlx-launch-start --ports 8101` correctly refused partial scope without `--allow-partial`
- Gateway alias smoke (LiteLLM with key):
  - `deep` => `deep-ok`
  - `main` => `main-ok`
  - `fast` => `fast-ok`

## Notes
- `listener_visible=false` remains expected in some root-owned launchd cases; `http_models_ok=true` is now the serving-truth signal in `status --checks`.
