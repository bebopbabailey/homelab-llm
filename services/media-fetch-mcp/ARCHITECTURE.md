# Architecture: media-fetch-mcp

`media-fetch-mcp` is a Mini-owned localhost-only MCP backend for retrieval
helpers that should be usable from Open WebUI and future pipelines without
going through LiteLLM.

Phase 1 shape:
- Python FastMCP service
- Streamable HTTP on `127.0.0.1:8012`
- one read-only tool: `youtube.transcript`

Why this service exists separately:
- Open WebUI requires Streamable HTTP MCP, not stdio.
- Transcript retrieval is tool behavior, not model behavior.
- This keeps YouTube/media ingestion separate from LiteLLM task aliases and
  leaves room for future document/media retrieval tools under the same service.

Current non-goals:
- summarization
- translation
- chunking
- retrieval indexing
- TinyAgents stdio registry wiring
