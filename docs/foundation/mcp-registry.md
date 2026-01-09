# MCP Registry (Template)

This file defines a simple, durable registry for MCP servers and tools. It is
intended to be the single source of truth for tool endpoints and transports.

## Recommended Location
- `/etc/homelab-llm/mcp-registry.json` (runtime, not in repo)

## JSON Schema (v1)
```json
{
  "version": 1,
  "servers": [
    {
      "name": "searxng-search",
      "purpose": "web search",
      "transport": "http",
      "endpoint": "http://127.0.0.1:8888",
      "health": "http://127.0.0.1:8888/health",
      "env": [
        "SEARXNG_SETTINGS_PATH"
      ],
      "tools": [
        "search.web"
      ],
      "notes": "Local-only; behind firewall"
    }
  ]
}
```

## Field Notes
- `transport`: `stdio` or `http` (HTTP/SSE).
- `endpoint`: URL for HTTP/SSE servers; command for stdio servers can be stored
  in `command` and `args`.
- `tools`: human-readable tool identifiers exposed by the server.

## stdio Example
```json
{
  "name": "local-repo-tools",
  "purpose": "repo analysis",
  "transport": "stdio",
  "command": "/usr/local/bin/repo-tools-server",
  "args": ["--root", "/home/christopherbailey/homelab-llm"],
  "tools": ["repo.scan", "repo.stats"]
}
```

