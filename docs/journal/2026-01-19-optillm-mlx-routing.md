# 2026-01-19 — OptiLLM routing for MLX handles

**Status:** Deprecated. Routing MLX handles through OptiLLM is no longer used.

## Summary
All MLX handles now route through OptiLLM with intelligent routing enabled.

## Wiring
- Client calls: `model=mlx-...`
- LiteLLM forwards to OptiLLM on the Studio at `192.168.1.72:4020` (via `OPTILLM_API_BASE`).
- OptiLLM keeps the `router-` prefix for upstream calls.
- LiteLLM maps `router-mlx-*` models **directly** to MLX ports.

This avoids the OptiLLM → LiteLLM → OptiLLM loop while keeping user-facing
handles unchanged. The `router-mlx-*` models are internal (not in
`layer-gateway/registry/handles.jsonl`) but do appear in LiteLLM `/v1/models`.

## Changes
- Added `router-mlx-*` entries in `layer-gateway/litellm-orch/config/router.yaml`.
- Routed MLX handles to OptiLLM in `layer-gateway/litellm-orch/config/env.local`.
- Patched OptiLLM `parse_combined_approach` to preserve the `router-` prefix
  in model names (keeps router enabled while avoiding loops).
- Router plugin load fix to avoid meta tensor errors.

## Files
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/config/env.local`
- `layer-gateway/optillm-proxy/README.md`
- `layer-gateway/optillm-proxy/.venv/lib/python3.11/site-packages/optillm/server.py`
- `layer-gateway/optillm-proxy/.venv/lib/python3.11/site-packages/optillm/plugins/router_plugin.py`
