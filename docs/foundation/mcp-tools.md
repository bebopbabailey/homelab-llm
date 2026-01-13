# MCP Tools (Implemented Locally)

## Purpose
MCP servers expose tools that agents can call. In this platform:
- **LLM calls** go through LiteLLM only.
- **Tool calls** go through MCP servers.

TinyAgents is the default MCP client for the MVP.

## Current Status
- MCP stdio tools are implemented (`web.fetch`, `search.web`) and run locally on the Mini.
- MCP registry and systemd wiring are MVP work items.

## How LLMs Use MCP
LLMs do not talk to MCP servers directly.
An agent runtime (e.g., TinyAgents) interprets the model output, selects tools,
and calls MCP servers, then feeds results back to the LLM via the same
conversation.

## MCP Server Inventory (pending registry)
Maintain a simple registry of MCP servers with:
- Name and purpose
- Transport (stdio vs HTTP/SSE)
- Endpoint or command
- Required environment variables

## Tool Contract Guidelines
- Document inputs, outputs, and error cases.
- Version tool schemas to avoid breaking changes.
- Keep tools small and composable.
- `python.run` is a future tool and must be sandboxed with explicit allowlist
  and confirmation for untrusted execution.

## Near-term Tool Candidate
- `transcript.clean`: wraps `benny-clean-m` with a fixed system prompt and
  returns only cleaned text (no commentary).

## Web Search + Fetch (implemented)
Search is only the first step. A durable pipeline also needs a fetch/clean
stage that returns readable text for models and schemas.

### `web.fetch` (implemented)
Purpose: fetch a URL and return a cleaned, model-ready payload.

Recommended output fields:
- `final_url`, `title`, `byline`, `published_at`, `lang`
- `clean_text` (primary)
- `raw_html` (optional, for strict schema extraction)
- `links` (optional, for follow-up fetches)

Recommended libraries (best coverage without being brittle):
- `trafilatura`: strong, modern extraction for messy pages.
- `readability-lxml`: good fallback for classic “main article” pages.
- `selectolax` or `lxml`: fast HTML parse + tag cleanup.

Use `trafilatura` first, fallback to `readability-lxml`, and keep `raw_html`
when a schema-based extractor needs it.

### Schematron input note
Schematron does not use prompts; it only consumes the schema and input text.
Provide trimmed, relevant HTML or clean text to improve extraction fidelity.

### MCP server note
`web.fetch` and `search.web` are implemented as a stdio MCP tool server under
`services/web-fetch` and are launched by the agent runtime.
