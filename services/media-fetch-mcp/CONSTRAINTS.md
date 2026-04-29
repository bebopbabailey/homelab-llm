# Constraints: media-fetch-mcp

This service inherits global constraints from `../../CONSTRAINTS.md`.

## Hard constraints
- Bindings stay localhost-only on the Mini.
- This service is a tool backend, not an LLM gateway or summarization service.
- `youtube.transcript` is retrieval-only in this phase.
- No translation fallback in v1.
- No chunking, truncation, or storage layer in v1.
- No new LAN exposure, auth bypass, or external callback behavior.

## Allowed operations
- Add a localhost-only Streamable HTTP MCP backend.
- Add read-only transcript retrieval through `youtube-transcript-api`.
- Add systemd, env template, and docs for the localhost-only backend.

## Forbidden operations
- Adding LiteLLM routing for this service.
- Adding TinyAgents stdio registry wiring in this slice.
- Adding write tools or any mutation of external systems.

## Validation pointers
- `uv run python -m unittest tests.test_media_fetch_mcp`
- direct MCP client connect against `http://127.0.0.1:8012/mcp`
- Open WebUI MCP verify against `http://127.0.0.1:8012/mcp`
