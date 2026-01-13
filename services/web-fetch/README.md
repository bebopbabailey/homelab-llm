# Web Fetch (MCP stdio tool)

## Purpose
Fetch a URL and return cleaned, model-ready text for downstream use in search,
summarization, or schema extraction.

## Status
Implemented (stdio MCP tool). Uses `trafilatura` with `readability-lxml` fallback.
Runs locally via an MCP client; not a systemd service yet.

## Tools exposed
- `search.web` (via LiteLLM `/v1/search`)
- `web.fetch`

## Run (dev)
```bash
cd /home/christopherbailey/homelab-llm/services/web-fetch
uv venv .venv
uv pip install -e .
web-fetch-mcp
```

## Demo client
```bash
.venv/bin/python3 scripts/demo_client.py
```

Print clean text only:
```bash
.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text
```

Call search via MCP:
```bash
.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3
```

## Env
- `WEB_FETCH_USER_AGENT` (optional): override user agent string.
- `LITELLM_SEARCH_API_BASE` (optional): LiteLLM search endpoint for `search.web`.
- `LITELLM_SEARCH_API_KEY` (optional): API key for LiteLLM search (default `dummy`).

## Tool Contract
See `docs/foundation/tool-contracts.md` (`web.fetch`).
