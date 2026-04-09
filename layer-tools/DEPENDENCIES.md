# Tools Layer Dependencies

This layer hosts tool services (search, MCP tools, observability helpers) used
by orchestrators/agents.

## Inbound
- LiteLLM calls tool backends where applicable (for example `/v1/search`).
- MCP stdio tools are invoked by a client.
- Open Terminal MCP is a long-running localhost-only HTTP service consumed
  directly by Open WebUI on the Mini.
- Any shared LiteLLM alias for this MCP surface remains future work.

## Services
- SearXNG (Mini): `http://127.0.0.1:8888`
- Open Terminal MCP (Mini): `http://127.0.0.1:8011/mcp`
- Prometheus (Mini): `http://127.0.0.1:9090`
- Prometheus (Mini): `http://127.0.0.1:9090`

## Source-of-truth pointers
- `docs/INTEGRATIONS.md`
- `docs/foundation/tool-contracts.md`
- `docs/foundation/mcp-registry.md`
