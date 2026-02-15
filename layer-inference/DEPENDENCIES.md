# Inference Layer Dependencies

This layer hosts or controls inference backends. Clients must not call these directly.

## Inbound
- LiteLLM (gateway) is the only intended caller for inference backends.

## Backends
- OpenVINO server (Mini): `http://127.0.0.1:9000`
- MLX Omni (Studio): `http://192.168.1.72:8100/v1`
- Orin: currently no active inference services (see `docs/foundation/orin-agx.md`)

## Source-of-truth pointers
- Topology: `docs/foundation/topology.md`
- MLX control plane: `docs/foundation/mlx-registry.md`

