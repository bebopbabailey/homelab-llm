# Service Spec: tiny-agents (planned)

## Purpose
TinyAgents is a lightweight agent/orchestrator client intended to call LiteLLM
as the single gateway. It is not a backend and should not be called by external
clients directly.

## Runtime
- **Language**: Python 3.10+
- **Dependency manager**: `uv` only
- **Deployment**: local process (no LAN exposure)

## Inbound/Outbound
- **Inbound**: none (CLI-driven)
- **Outbound**: LiteLLM `http://127.0.0.1:4000/v1`

## Configuration (planned)
- `LITELLM_API_BASE=http://127.0.0.1:4000/v1` (if/when TinyAgents is adapted)
- `HUGGINGFACEHUB_API_TOKEN` (only if HF InferenceClient is used)

## Constraints
- MCP usage is allowed but should be planned and documented before enabling.
- Do not bypass LiteLLM or call backends directly.
- Do not expose this service on LAN without approval.
