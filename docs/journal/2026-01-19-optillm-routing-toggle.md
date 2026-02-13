# 2026-01-19 — OptiLLM routing toggle (mlxctl)

**Status:** Deprecated. Routing MLX handles through OptiLLM is no longer used.

## Summary
Added a simple on/off switch to route MLX handles through OptiLLM without
changing user-facing handles.

## Toggle
- On: `mlxctl sync-gateway --route-via-optillm`
- Off: `mlxctl sync-gateway --no-route-via-optillm`
- Default: `MLX_ROUTE_VIA_OPTILLM=1`

## Behavior (when enabled)
- MLX handles point to OptiLLM on the Studio (`192.168.1.72:4020`).
- OptiLLM calls LiteLLM using `router-mlx-*` model names.
- LiteLLM maps `router-mlx-*` entries directly to MLX ports.
- `router-mlx-*` entries are internal (not in `handles.jsonl`) but appear in `/v1/models`.

## Files
- `platform/ops/scripts/mlxctl`
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/config/env.local`
