# Tools Layer Dependencies

This layer hosts tool services (search, MCP tools) used by orchestrators/agents.

## Inbound
- LiteLLM (gateway) calls tool backends where applicable (e.g., `/v1/search`).
- MCP stdio tools are invoked by a client (not a long-running server).

## Services
- SearXNG (Mini): `http://127.0.0.1:8888`

## Source-of-truth pointers
- Integrations: `docs/INTEGRATIONS.md`
- Tool contracts: `docs/foundation/tool-contracts.md`
- MCP registry: `docs/foundation/mcp-registry.md`

