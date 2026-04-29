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
        "required": ["title", "url", "snippet", "date"],
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
- status: active
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
    "include_raw_html": { "type": "boolean", "default": false },
    "output_mode": { "type": "string", "enum": ["text", "evidence"], "default": "text" }
  }
}
```
- output_schema:
```json
{
  "oneOf": [
    {
      "type": "object",
      "required": [
        "final_url",
        "title",
        "byline",
        "published_at",
        "lang",
        "clean_text",
        "extractor_used",
        "content_type",
        "http_status",
        "content_sha256"
      ],
      "additionalProperties": false,
      "properties": {
        "final_url": { "type": "string", "format": "uri" },
        "title": { "type": ["string", "null"] },
        "byline": { "type": ["string", "null"] },
        "published_at": { "type": ["string", "null"] },
        "lang": { "type": ["string", "null"] },
        "clean_text": { "type": "string", "minLength": 1 },
        "extractor_used": { "type": "string", "enum": ["trafilatura", "readability", "plain_text"] },
        "content_type": { "type": "string", "enum": ["text/html", "application/xhtml+xml", "text/plain"] },
        "http_status": { "type": "integer", "minimum": 200, "maximum": 299 },
        "content_sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
        "raw_html": { "type": "string" }
      }
    },
    {
      "type": "object",
      "required": [
        "final_url",
        "title",
        "byline",
        "published_at",
        "lang",
        "clean_text",
        "extractor_used",
        "content_type",
        "http_status",
        "content_sha256",
        "markdown",
        "canonical_url",
        "site_name",
        "description",
        "links",
        "quality_label",
        "quality_flags",
        "content_stats"
      ],
      "additionalProperties": false,
      "properties": {
        "final_url": { "type": "string", "format": "uri" },
        "title": { "type": ["string", "null"] },
        "byline": { "type": ["string", "null"] },
        "published_at": { "type": ["string", "null"] },
        "lang": { "type": ["string", "null"] },
        "clean_text": { "type": "string", "minLength": 1 },
        "extractor_used": { "type": "string", "enum": ["trafilatura", "readability", "plain_text"] },
        "content_type": { "type": "string", "enum": ["text/html", "application/xhtml+xml", "text/plain"] },
        "http_status": { "type": "integer", "minimum": 200, "maximum": 299 },
        "content_sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
        "raw_html": { "type": "string" },
        "markdown": { "type": "string", "minLength": 1 },
        "canonical_url": { "type": ["string", "null"], "format": "uri" },
        "site_name": { "type": ["string", "null"] },
        "description": { "type": ["string", "null"] },
        "links": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["text", "url"],
            "additionalProperties": false,
            "properties": {
              "text": { "type": "string" },
              "url": { "type": "string", "format": "uri" }
            }
          }
        },
        "quality_label": { "type": "string", "enum": ["high", "medium", "low"] },
        "quality_flags": {
          "type": "array",
          "items": { "type": "string" }
        },
        "content_stats": {
          "type": "object",
          "required": ["chars", "words", "heading_count", "list_count", "code_block_count", "link_count"],
          "additionalProperties": false,
          "properties": {
            "chars": { "type": "integer", "minimum": 0 },
            "words": { "type": "integer", "minimum": 0 },
            "heading_count": { "type": "integer", "minimum": 0 },
            "list_count": { "type": "integer", "minimum": 0 },
            "code_block_count": { "type": "integer", "minimum": 0 },
            "link_count": { "type": "integer", "minimum": 0 }
          }
        }
      }
    }
  ]
}
```
- errors:
```json
[
  { "code": "invalid_url", "http_status": 400 },
  { "code": "url_not_allowed", "http_status": 403 },
  { "code": "redirect_not_allowed", "http_status": 403 },
  { "code": "redirect_limit_exceeded", "http_status": 508 },
  { "code": "mime_not_allowed", "http_status": 415 },
  { "code": "body_too_large", "http_status": 413 },
  { "code": "upstream_failure", "http_status": 502 },
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

## youtube.transcript
- status: active
- transport: mcp (http via `127.0.0.1:8012/mcp`)
- endpoint: `media-fetch` (MCP server name)
- input_schema:
```json
{
  "type": "object",
  "required": ["url"],
  "additionalProperties": false,
  "properties": {
    "url": { "type": "string", "format": "uri" }
  }
}
```
- output_schema:
```json
{
  "type": "object",
  "required": ["video_id", "transcript_text", "language", "caption_type"],
  "additionalProperties": false,
  "properties": {
    "video_id": { "type": "string", "pattern": "^[A-Za-z0-9_-]{11}$" },
    "transcript_text": { "type": "string", "minLength": 1 },
    "language": { "type": "string", "minLength": 1 },
    "caption_type": { "type": "string", "enum": ["manual", "generated"] }
  }
}
```
- errors:
```json
[
  { "code": "invalid_url", "http_status": 400 },
  { "code": "unsupported_url", "http_status": 400 },
  { "code": "no_transcript", "http_status": 404 },
  { "code": "upstream_failure", "http_status": 502 }
]
```

## health_check
- status: active on direct Open Terminal MCP backend; LiteLLM alias not yet live
- transport: mcp (http via `127.0.0.1:8011/mcp`)
- endpoint: direct backend
- input_schema:
```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}
```
- output_schema:
```json
{
  "type": "object"
}
```

## list_files
- status: active on direct Open Terminal MCP backend; LiteLLM alias not yet live
- transport: mcp (http via `127.0.0.1:8011/mcp`)
- endpoint: direct backend
- input_schema:
```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "directory": { "type": "string", "default": "." }
  }
}
```

## read_file
- status: active on direct Open Terminal MCP backend; LiteLLM alias not yet live
- transport: mcp (http via `127.0.0.1:8011/mcp`)
- endpoint: direct backend
- input_schema:
```json
{
  "type": "object",
  "required": ["path"],
  "additionalProperties": false,
  "properties": {
    "path": { "type": "string", "minLength": 1 },
    "start_line": { "type": "integer", "minimum": 1 },
    "end_line": { "type": "integer", "minimum": 1 }
  }
}
```

## grep_search
- status: active on direct Open Terminal MCP backend; LiteLLM alias not yet live
- transport: mcp (http via `127.0.0.1:8011/mcp`)
- endpoint: direct backend
- input_schema:
```json
{
  "type": "object",
  "required": ["query"],
  "additionalProperties": false,
  "properties": {
    "query": { "type": "string", "minLength": 1 },
    "path": { "type": "string", "default": "." },
    "regex": { "type": "boolean", "default": false },
    "case_insensitive": { "type": "boolean", "default": false },
    "include": { "type": "string" },
    "match_per_line": { "type": "boolean", "default": false },
    "max_results": { "type": "integer", "minimum": 1 }
  }
}
```

## glob_search
- status: active on direct Open Terminal MCP backend; LiteLLM alias not yet live
- transport: mcp (http via `127.0.0.1:8011/mcp`)
- endpoint: direct backend
- input_schema:
```json
{
  "type": "object",
  "required": ["pattern"],
  "additionalProperties": false,
  "properties": {
    "pattern": { "type": "string", "minLength": 1 },
    "path": { "type": "string", "default": "." },
    "exclude": { "type": "string" },
    "type": { "type": "string", "enum": ["file", "directory", "all"] },
    "max_results": { "type": "integer", "minimum": 1 }
  }
}
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
