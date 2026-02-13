# Service Spec: tiny-agents (MVP orchestration)

## Purpose
TinyAgents is a lightweight agent/orchestrator client intended to call LiteLLM
as the single gateway. It is not a backend and should not be called by external
clients directly.

## Runtime
- **Language**: Python 3.10+
- **Dependency manager**: `uv` only
- **Deployment**: local process (MVP), optional systemd/launchd wrapper

## Inbound/Outbound
- **Inbound (CLI mode)**: none
- **Inbound (service mode)**: HTTP on `127.0.0.1:4030` only
- **Outbound**: LiteLLM `http://127.0.0.1:4000/v1`

## Configuration (MVP)
- `LITELLM_API_BASE=http://127.0.0.1:4000/v1`
- `LITELLM_API_KEY_ENV=LITELLM_API_KEY`
- `MCP_REGISTRY_PATH=/etc/homelab-llm/mcp-registry.json`
- `TINY_AGENTS_HOST=127.0.0.1`
- `TINY_AGENTS_PORT=4030`

## Endpoints (service mode)
- `GET /health` → `{ "status": "ok" }`
- `POST /run`
  - request: model + messages + optional allowlist/tool controls
  - response: run metadata, tool call records, final assistant message

## Constraints
- MCP usage is allowed and should be documented in the registry.
- Do not bypass LiteLLM or call backends directly.
- Do not expose this service on LAN without approval.
