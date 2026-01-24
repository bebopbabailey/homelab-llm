# LiteLLM: direct MLX routing + handle pruning

## Summary
- Removed OpenVINO handles from the gateway registry and LiteLLM router config.
- Removed `router-mlx-*` entries and direct OptiLLM routing in LiteLLM.
- LiteLLM now exposes only actively used MLX handles.
- OptiLLM is used directly (port 4020) with `optillm_approach` in the request body.
- The old router-based wiring is deprecated in docs and configs.
- `mlxctl` no longer supports `--route-via-optillm` / `MLX_ROUTE_VIA_OPTILLM`.

## Files touched
- `layer-gateway/registry/handles.jsonl`
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/config/env.local`
- `layer-gateway/litellm-orch/config/env.example`
- `docs/INTEGRATIONS.md`
- `docs/foundation/mlx-registry.md`
- `layer-gateway/litellm-orch/README.md`
- `layer-gateway/optillm-proxy/README.md`
- `layer-gateway/optillm-proxy/SERVICE_SPEC.md`
- `platform/ops/systemd/optillm-proxy.service`
