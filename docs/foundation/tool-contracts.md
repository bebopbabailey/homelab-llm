# Tool Contracts (Living)

This document defines tool contracts in a strict, schema-first format. Treat
this as the source of truth for inputs, outputs, and errors.

Format:
- Each tool includes `name`, `status`, `transport`, `endpoint`, and JSON Schemas
  for input/output.
- Use these schemas to validate tool calls and responses.
- When a tool is HTTP-based, keep an OpenAPI 3.1 spec in sync with the JSON
  schemas here.
- When a tool is MCP-based, keep an MCP tool schema in sync with the JSON
  schemas here.

## OpenAPI vs MCP (required)
- OpenAPI documents HTTP transport contracts (paths, methods, auth, status).
- MCP tool schemas document tool call contracts across stdio or HTTP.
- For durability, maintain both when a tool is HTTP-accessible.

## search.web
- status: active (via MCP stdio, backed by LiteLLM `/v1/search`)
- transport: mcp (stdio)
- endpoint: `web-fetch` (MCP server name)
- input_schema:
```json
{
  "type": "object",
  "required": ["query"],
  "additionalProperties": false,
  "properties": {
    "query": { "type": "string", "minLength": 1 },
    "max_results": { "type": "integer", "minimum": 1, "maximum": 25 }
  }
}
```
- output_schema:
```json
{
  "type": "object",
  "required": ["results"],
  "additionalProperties": false,
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "url", "snippet"],
        "additionalProperties": false,
        "properties": {
          "title": { "type": "string" },
          "url": { "type": "string" },
          "snippet": { "type": "string" },
          "date": { "type": ["string", "null"] }
        }
      }
    }
  }
}
```
- errors:
```json
[
  { "code": "invalid_query", "http_status": 400 },
  { "code": "upstream_failure", "http_status": 502 },
  { "code": "timeout", "http_status": 504 }
]
```

## web.fetch
- status: planned
- transport: mcp (stdio)
- endpoint: `web-fetch` (MCP server name)
- input_schema:
```json
{
  "type": "object",
  "required": ["url"],
  "additionalProperties": false,
  "properties": {
    "url": { "type": "string", "format": "uri" },
    "include_raw_html": { "type": "boolean", "default": false }
  }
}
```
- output_schema:
```json
{
  "type": "object",
  "required": ["final_url", "clean_text"],
  "additionalProperties": false,
  "properties": {
    "final_url": { "type": "string", "format": "uri" },
    "title": { "type": ["string", "null"] },
    "byline": { "type": ["string", "null"] },
    "published_at": { "type": ["string", "null"] },
    "lang": { "type": ["string", "null"] },
    "clean_text": { "type": "string", "minLength": 1 },
    "raw_html": { "type": "string" }
  },
  "allOf": [
    {
      "if": { "properties": { "raw_html": { "type": "string" } } },
      "then": { "required": ["raw_html"] }
    }
  ]
}
```
- errors:
```json
[
  { "code": "fetch_failed", "http_status": 502 },
  { "code": "parse_failed", "http_status": 422 },
  { "code": "timeout", "http_status": 504 }
]
```

## transcript.clean
- status: planned
- transport: mcp (http or stdio server)
- endpoint: `transcript-clean` (MCP server name)
- input_schema:
```json
{
  "type": "object",
  "required": ["text"],
  "additionalProperties": false,
  "properties": {
    "text": { "type": "string", "minLength": 1 }
  }
}
```
- output_schema:
```json
{
  "type": "object",
  "required": ["clean_text"],
  "additionalProperties": false,
  "properties": {
    "clean_text": { "type": "string", "minLength": 1 }
  }
}
```
- errors:
```json
[
  { "code": "model_error", "http_status": 502 },
  { "code": "timeout", "http_status": 504 }
]
```

## mlx.load
- status: planned
- transport: mcp (stdio server on Mini)
- endpoint: `mlxctl` (wrapper to Studio)
- input_schema:
```json
{
  "type": "object",
  "required": ["model", "port"],
  "additionalProperties": false,
  "properties": {
    "model": { "type": "string", "minLength": 1 },
    "port": { "type": "integer", "minimum": 8100, "maximum": 8139 }
  }
}
```
- output_schema:
```json
{
  "type": "object",
  "required": ["ok", "message", "port", "model"],
  "additionalProperties": false,
  "properties": {
    "ok": { "type": "boolean" },
    "message": { "type": "string" },
    "port": { "type": "integer" },
    "model": { "type": "string" }
  }
}
```
- errors:
```json
[
  { "code": "invalid_port", "http_status": 400 },
  { "code": "model_not_found", "http_status": 404 },
  { "code": "port_busy", "http_status": 409 },
  { "code": "launch_failed", "http_status": 500 }
]
```

## mlx.unload
- status: planned
- transport: mcp (stdio server on Mini)
- endpoint: `mlxctl` (wrapper to Studio)
- input_schema:
```json
{
  "type": "object",
  "required": ["port"],
  "additionalProperties": false,
  "properties": {
    "port": { "type": "integer", "minimum": 8100, "maximum": 8139 }
  }
}
```
- output_schema:
```json
{
  "type": "object",
  "required": ["ok", "message", "port"],
  "additionalProperties": false,
  "properties": {
    "ok": { "type": "boolean" },
    "message": { "type": "string" },
    "port": { "type": "integer" }
  }
}
```
- errors:
```json
[
  { "code": "invalid_port", "http_status": 400 },
  { "code": "not_listening", "http_status": 404 }
]
```
