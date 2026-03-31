# Tools Layer

Mission: action/execution services (MCP tools, search) used by agents via the
gateway. Tools may touch external systems, so safety boundaries are strict.

Current service types in this layer:
- stdio MCP collection under `layer-tools/mcp-tools`
- localhost-only HTTP MCP service under `layer-tools/open-terminal`
- local search service `layer-tools/searxng`

See root docs: `/home/christopherbailey/homelab-llm/SYSTEM_OVERVIEW.md`.
Use `docs/` for deeper tools notes.
