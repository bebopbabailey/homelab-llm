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
- `transcript_text`
- `language`
- `caption_type`

It preserves source caption language, prefers manual captions when available,
and returns timestamped transcript lines with light normalization only.
