# 2026-01-19 — MLX model reset (pre-download)

## Context
We are reducing MLX models to a new 5-model baseline before re-registering
handles and OptiLLM router aliases. This aligns the registry with actual
on-disk models and keeps LiteLLM aliases accurate.

## Actions
- Removed all MLX model caches from Studio `~/models/hf/hub` and Seagate `og_models/mlx-hf`.
- Reset Studio MLX registry (`~/models/hf/hub/registry.json`) to empty.
- Synced gateway (`mlxctl sync-gateway`) to remove MLX entries from:
  - `layer-gateway/litellm-orch/config/router.yaml`
  - `layer-gateway/litellm-orch/config/env.local`
  - `layer-gateway/registry/handles.jsonl`
- Cleared MLX port map + OptiLLM ensemble defaults in `platform/ops/scripts/mlxctl`.
- Updated docs to reflect “no MLX models registered” state.

## Next
- Download and register the new 5-model baseline:
  - `mlx-community/gpt-oss-120b-MXFP4-Q4`
  - `mlx-community/Qwen3-235B-A22B-Instruct-2507-4bit`
  - `sjug/Mistral-Large-Instruct-2411-8bit`
  - `mlx-community/gemma-3-27b-it-qat-4bit`
  - `mlx-community/gpt-oss-20b-MXFP4-Q4`
- Rebuild MLX port assignments, LiteLLM routing, and OptiLLM router handles.
