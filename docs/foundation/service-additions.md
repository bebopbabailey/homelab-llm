# Adding Services and Backends

This repo treats LiteLLM as the only client-facing entry point. New services
should either be:
- A backend that LiteLLM routes to, or
- A client/orchestrator that calls LiteLLM (never backends directly).
Optimization proxies (e.g., OptiLLM) must sit behind LiteLLM and bind to localhost only.

## Before You Start
- Confirm you are not adding a new LAN-exposed service without approval.
- Ports are immutable; do not reuse or change existing ones.
- Use `uv` for Python services; avoid system Python changes.

## Service Checklist (required)
- `SERVICE_SPEC.md` present with run/health/env details.
- `ARCHITECTURE.md` updated with role in the mesh.
- `AGENTS.md` created with service-scoped guidance.
- `platform/ops/scripts/healthcheck.sh` updated if new endpoints exist.
- `platform/ops/scripts/restart-all.sh` updated if new systemd service added.
- Systemd unit added under `platform/ops/systemd/` when applicable.
- `docs/foundation/topology.md` and `docs/PLATFORM_DOSSIER.md` updated.

## MCP Tool Checklist (when applicable)
- Document tool purpose, inputs, outputs, and failure modes.
- Declare transport (stdio vs HTTP/SSE) and any required ports.
- Add tool server to the MCP tool registry (planned).
- Ensure LiteLLM remains the LLM gateway; tools are separate.

## Add a New Backend (LiteLLM-routed)
1) Create service directory under the appropriate `layer-*/<name>` folder.
2) Provide a service contract:
   - `layer-*/<name>/SERVICE_SPEC.md` (host, endpoints, env, health).
   - `layer-*/<name>/ARCHITECTURE.md` (role in the mesh).
3) Ensure the backend exposes:
   - `POST /v1/chat/completions`
   - `GET /v1/models`
   - `GET /health`
4) Add routing in LiteLLM:
   - Update `layer-gateway/litellm-orch/config/router.yaml`.
   - Add env vars to `layer-gateway/litellm-orch/config/env.local` (not committed).
   - Use plain logical model names (`jerry-*` style).
5) Update topology docs:
   - `docs/foundation/topology.md`
   - `docs/PLATFORM_DOSSIER.md`
6) Validate with health checks:
   - `platform/ops/scripts/healthcheck.sh` (extend if needed).
   - `layer-gateway/litellm-orch/scripts/health-check.sh` for LiteLLM.

## Add a New Client/Orchestrator (TinyAgents)
1) Client must call LiteLLM only (`http://192.168.1.71:4000/v1`).
2) Add env vars for model selection (`*_API_BASE`, `*_MODEL`) and
   keep them out of git.
3) Document the client contract in `docs/` and its service folder.

## Config Sources of Truth
- LiteLLM routing: `layer-gateway/litellm-orch/config/router.yaml`.
- LiteLLM env: `layer-gateway/litellm-orch/config/env.local` (local only).
- Open WebUI env: `/etc/open-webui/env`.
- OpenVINO env: `/etc/homelab-llm/ov-server.env`.
