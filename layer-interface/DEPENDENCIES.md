# Interface Layer Dependencies

This layer owns client/UI surfaces plus the Orin speech facade. It must not
depend on external inference backends directly for LLM traffic.

## Primary upstream
- LiteLLM (Mini)

## Allowed downstream services
- Open WebUI: `http://127.0.0.1:3000`
- Grafana: `http://127.0.0.1:3001`
- OpenCode Web: `http://127.0.0.1:4096` locally, tailnet operator path via
  `svc:codeagent`
- Voice Gateway: `http://192.168.1.93:18080/v1` as the approved speech facade

## Forbidden direct dependencies
- MLX Studio endpoints
- OpenVINO on Mini
- OptiLLM proxy on Studio

## Source-of-truth pointers
- Topology: `docs/foundation/topology.md`
- Integrations: `docs/INTEGRATIONS.md`
