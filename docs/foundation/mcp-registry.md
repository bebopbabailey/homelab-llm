# MCP Registry (Template)

This file defines a simple, durable registry for MCP servers and tools. It is
intended to be the single source of truth for tool endpoints and transports.

## Recommended Location
- `/etc/homelab-llm/mcp-registry.json` (runtime, not in repo)
- Status: not created yet; MVP will write this file.
- Template: `ops/templates/mcp-registry.json`.

## JSON Schema (v1)
```json
{
  "version": 1,
  "servers": [
    {
      "name": "web-fetch",
      "purpose": "fetch + clean HTML",
      "transport": "stdio",
      "command": "/home/christopherbailey/homelab-llm/services/web-fetch/web_fetch_mcp.py",
      "args": [],
      "env": [
        "LITELLM_SEARCH_API_BASE",
        "LITELLM_SEARCH_API_KEY",
        "WEB_FETCH_USER_AGENT"
      ],
      "tools": [
        "search.web",
        "web.fetch"
      ],
      "notes": "Returns cleaned text plus optional raw HTML."
    }
  ]
}
```

## Field Notes
- `transport`: `stdio` or `http` (HTTP/SSE).
- `endpoint`: URL for HTTP/SSE servers; command for stdio servers can be stored
  in `command` and `args`.
- `tools`: human-readable tool identifiers exposed by the server.
- Consider a future `python.run` tool only with strict sandboxing and
  confirmation prompts for untrusted code.

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

## Tool Schema Example: `web.fetch`
```json
{
  "name": "web.fetch",
  "description": "Fetch a URL and return cleaned, model-ready content.",
  "input": {
    "url": "https://example.com/article",
    "include_raw_html": false
  },
  "output": {
    "final_url": "https://example.com/article",
    "title": "Example Article",
    "byline": "Author Name",
    "published_at": "2025-01-01T00:00:00Z",
    "lang": "en",
    "clean_text": "Extracted text...",
    "raw_html": "<html>...</html>"
  }
}
```
