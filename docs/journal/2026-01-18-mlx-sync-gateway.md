# 2026-01-18 — MLX Port Policy + Gateway Sync

## Summary
- Expanded MLX port policy: team range 8100–8119, experimental range 8120–8139.
- MLX registry is the source of truth; gateway configs are synchronized from it.
- No placeholders: handles/router entries exist only for loaded models with ports.
- Synchronization is automated and safe for agent use.

## Contract
- Load order: service started → MLX registry updated → LiteLLM router/env updated → handles updated.
- Experimental models load into the lowest free port in 8120–8139 (`mlxctl load <model> auto`).
- Promotions to team ports are explicit by choosing a port in 8100–8119.
- No model directory → no port assignment → no handle/router entry.

## Tooling
- `mlxctl sync-gateway` updates:
  - `layer-gateway/litellm-orch/config/router.yaml`
  - `layer-gateway/litellm-orch/config/env.local`
  - `layer-gateway/registry/handles.jsonl`
- `mlxctl load` and `mlxctl ensure` sync by default after successful loads.
- `mlxctl assign-team` assigns all MLX models to team ports by on-disk size, with OptiLLM
  ensemble models filling 8100–8109 first and remaining models in 8110–8119.
- Planned models table will capture size-on-disk / memory footprint for ordering.
- MLX registry now includes `source_path` to provide a durable link from model_id to the source artifact.
- OptiLLM v0 ensemble matrix documented at `layer-gateway/optillm-proxy/ENSEMBLES.md`.
