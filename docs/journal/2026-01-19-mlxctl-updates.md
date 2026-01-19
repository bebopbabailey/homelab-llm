# 2026-01-19 — mlxctl command updates

## Summary
Updated `mlxctl` commands to reflect current defaults and routing behavior.

## Changes
- `list` includes `context_length` and `max_output_tokens` columns.
- `load` / `ensure` now set defaults if missing:
  - `context_length`: inferred from model `config.json` when available; fallback 131072
  - `max_output_tokens`: default 64000
- `unload` / `unload-all` now sync the gateway by default (use `--no-sync` to skip).
- `reconcile` / `verify` check OptiLLM routing state when routing is enabled.
- `ensemble` command is deprecated (use `load`/`assign-team`).

## Files
- `platform/ops/scripts/mlxctl`
- `docs/foundation/mlx-registry.md`
