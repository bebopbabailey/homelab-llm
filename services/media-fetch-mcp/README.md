# media-fetch-mcp

Localhost-only MCP backend for read-only media retrieval tools.

Current tool:
- `youtube.transcript`

Run locally:
```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv venv .venv
uv pip install -e .
uv run python -m media_fetch_mcp --transport streamable-http --host 127.0.0.1 --port 8012
```

The tool accepts a supported single-video YouTube URL and returns:
- `video_id`
- `source_url`
- `transcript_text`
- `language`
- `language_code`
- `caption_type`
- `segments[]` with `text`, `start`, `duration`, and `timestamp_label`

It preserves source caption language, prefers manual captions when available,
returns timestamped transcript lines with light normalization only, and exposes
structured segments for downstream chunking/indexing consumers.
