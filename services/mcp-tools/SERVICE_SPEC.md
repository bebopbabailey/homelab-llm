# Service Spec: mcp-tools (stdio)

## Role
Provide MCP tools that are invoked over stdio by an MCP client.

## Exposure
- No ports.
- No LAN exposure.

## Primary tools
- `web.fetch` / `search.web` live under `web-fetch/`.

## Dependencies
- Some tools may call LiteLLM endpoints (e.g., `search.web` -> LiteLLM `/v1/search/searxng-search`).

