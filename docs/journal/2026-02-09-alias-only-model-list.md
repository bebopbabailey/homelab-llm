# 2026-02-09 — Alias‑Only LiteLLM Model List

## Goal
Remove duplicate canonical MLX model IDs from LiteLLM `/v1/models` while keeping
aliases (`main/deep/fast/swap`) as the only exposed handles.

## Changes
- `mlxctl sync-gateway` now omits canonical `mlx-*` entries in `router.yaml`.
- Canonical model IDs remain in the MLX registry and env vars for routing.

## Notes
- Clients (Open WebUI, OpenCode) should see only aliases and task handles.
