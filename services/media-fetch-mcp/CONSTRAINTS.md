# Constraints: media-fetch-mcp

This service inherits global constraints from `../../CONSTRAINTS.md`.

## Hard constraints
- Bindings stay localhost-only on the Mini.
- This service is a tool backend, not an LLM gateway or summarization service.
- `youtube.transcript` remains retrieval-only.
- Web helpers may orchestrate search/fetch/store/retrieve, but they must not
  call a model or synthesize an answer.
- No translation fallback in the transcript path.
- No new LAN exposure, auth bypass, or external callback behavior.

## Allowed operations
- Add a localhost-only Streamable HTTP MCP backend.
- Add read-only transcript retrieval through `youtube-transcript-api`.
- Add direct local SearXNG search and cleaned public-web fetch/extraction.
- Add direct `vector-db` session upsert/search/delete helpers that remain scoped
  to deterministic per-conversation `research:<conversation_id>` documents.
- Add systemd, env template, and docs for the localhost-only backend.

## Forbidden operations
- Adding LiteLLM routing for this service.
- Adding TinyAgents stdio registry wiring in this slice.
- Adding paid/hosted providers to the primary path.
- Adding internal browser automation for JS-heavy pages in this slice.

## Validation pointers
- `uv run python -m unittest tests.test_media_fetch_mcp`
- direct MCP client connect against `http://127.0.0.1:8012/mcp`
- direct SearXNG + `vector-db` smoke from `media-fetch-mcp`
- Open WebUI MCP verify against `http://127.0.0.1:8012/mcp`
