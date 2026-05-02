# media-fetch-mcp

Localhost-only MCP backend for reusable retrieval primitives on the Mini.

Current tool surface:
- `youtube.transcript`
- `media-fetch.web.search`
- `media-fetch.web.fetch`
- `media-fetch.web.session.upsert`
- `media-fetch.web.session.search`
- `media-fetch.web.session.delete`
- `media-fetch.web.quick`
- `media-fetch.web.research`

Run locally:
```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv venv .venv
uv pip install -e .
uv run python -m media_fetch_mcp --transport streamable-http --host 127.0.0.1 --port 8012
```

Core behaviors:
- `youtube.transcript` fetches full caption transcripts for supported YouTube
  video URLs and returns both timestamped flat text and structured segments.
- `media-fetch.web.search` calls local SearXNG directly and returns normalized
  live web results.
- `media-fetch.web.fetch` turns a public webpage into a cleaned evidence
  payload using `trafilatura` first, `readability-lxml` second, and plain-text
  fallback last.
- `media-fetch.web.session.*` stores and retrieves cleaned web evidence inside
  `vector-db` under deterministic per-conversation document ids:
  `research:<conversation_id>`.
- `media-fetch.web.quick` and `media-fetch.web.research` are orchestration
  helpers only. They do search, fetch, persist, and retrieve, but they do not
  call a model or synthesize answers.

The service stays localhost-only, reuses existing repo extraction logic, and is
meant to be the canonical retrieval boundary for Open WebUI and future
pipelines without relying on Open WebUI's native web-search ingestion path.
