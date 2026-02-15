# Gateway Layer Dependencies

This layer provides the single gateway for clients (LiteLLM) and proxy/orchestration services.

## Inbound
- Clients (UI + tools + automation) must call LiteLLM only.

## Outbound (primary upstreams)
- MLX Omni (Studio): `http://192.168.1.72:8100/v1`
- OpenVINO server (Mini): `http://127.0.0.1:9000`
- OptiLLM proxy (Studio): `http://192.168.1.72:4020/v1` (via LiteLLM `boost`)
- SearXNG (Mini): `http://127.0.0.1:8888`

## Source-of-truth pointers
- Topology: `docs/foundation/topology.md`
- Integrations: `docs/INTEGRATIONS.md`
- MLX control plane: `docs/foundation/mlx-registry.md`

