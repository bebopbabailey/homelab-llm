# Architecture: media-fetch-mcp

`media-fetch-mcp` is a Mini-owned localhost-only MCP backend for retrieval
helpers that should be usable from Open WebUI and future pipelines without
depending on Open WebUI's native web-search path.

Current shape:
- Python FastMCP service
- Streamable HTTP on `127.0.0.1:8012`
- media retrieval primitive: `youtube.transcript`
- web retrieval primitives:
  - `media-fetch.web.search`
  - `media-fetch.web.fetch`
  - `media-fetch.web.session.*`
  - `media-fetch.web.quick`
  - `media-fetch.web.research`

Why this service exists separately:
- Open WebUI requires Streamable HTTP MCP, not stdio.
- Transcript retrieval and web retrieval are tool behavior, not model behavior.
- The repo already had useful extraction logic in the stdio `web-fetch`
  service; this service is the HTTP/MCP boundary that can expose those
  primitives cleanly to Open WebUI and later pipelines.
- `SearXNG` remains the live web search broker.
- `vector-db` remains the durable retrieval substrate.
- `media-fetch-mcp` is the orchestrator that normalizes search, extraction, and
  session payloads for callers.

Runtime flow:
1. `media-fetch.web.search` -> direct SearXNG JSON search
2. `media-fetch.web.fetch` -> public-web fetch + extract/normalize
3. `media-fetch.web.session.upsert/search/delete` -> direct `vector-db` calls
4. `media-fetch.web.quick/research` -> reusable orchestration over 1-3

Current non-goals:
- internal LLM summarization
- translation
- browser-rendered JS page support
- paid hosted search/extraction providers
- TinyAgents stdio registry wiring
