# Interface Layer Dependencies

This layer is client/UI only. It must not depend on external inference backends
directly.

## Primary upstream
- LiteLLM (Mini):
  - Base URL (on-host): `http://127.0.0.1:4000/v1`
  - Auth: bearer token required (see `layer-gateway/litellm-orch/config/env.local`, not committed)

Note: some Interface services run on other hosts (e.g., Voice Gateway on Orin)
and will call LiteLLM over the LAN. In those cases, do not assume localhost for
`LITELLM_BASE_URL`.

Voice Gateway exception boundary:
- Voice Gateway runs on Orin and remains an Interface-layer service boundary.
- It may run local STT/TTS engines inside its own service boundary
  (current backend: localhost-only Speaches).
- It exposes the approved LAN speech facade used by LiteLLM.
- Future LLM calls from Voice Gateway must still go through LiteLLM.

## Allowed downstream services (read-only)
- Open WebUI: `http://127.0.0.1:3000` (UI)
- Grafana: `http://127.0.0.1:3001` (dashboards)

## Forbidden direct dependencies
- MLX (Studio) endpoints (e.g. `http://192.168.1.72:8100/v1`) must not be called directly from this layer.
- OpenVINO server (Mini `:9000`) must not be called directly from this layer.
- OptiLLM proxy (Studio `:4020`) must not be called directly from this layer.

## Source-of-truth pointers
- Topology: `docs/foundation/topology.md`
- Integrations: `docs/INTEGRATIONS.md`
