# Service Spec: tiny-agents (MVP orchestration)

## Purpose
TinyAgents is a lightweight agent/orchestrator client intended to call LiteLLM
as the single gateway. It is not a backend and should not be called by external
clients directly.

## Runtime
- **Language**: Python 3.10+
- **Dependency manager**: `uv` only
- **Deployment**: local process (MVP), systemd service target (no LAN exposure)

## Inbound/Outbound
- **Inbound**: none (CLI-driven)
- **Outbound**: LiteLLM `http://127.0.0.1:4000/v1`

## Configuration (MVP)
- `LITELLM_API_BASE=http://127.0.0.1:4000/v1`
- `HUGGINGFACEHUB_API_TOKEN` (only if HF InferenceClient is used)
- `MCP_REGISTRY_PATH=/etc/homelab-llm/mcp-registry.json`

## Constraints
- MCP usage is allowed and should be documented in the registry.
- Do not bypass LiteLLM or call backends directly.
- Do not expose this service on LAN without approval.
