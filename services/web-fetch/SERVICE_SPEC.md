# Web Fetch (MCP stdio)

## Purpose
Provide a local MCP stdio tool that fetches a URL and returns cleaned text
for LLM consumption.

## Run
- Command: `web-fetch-mcp`
- Transport: stdio (MCP)
- Host: Mini (local only)

## Tools
- `search.web` (via LiteLLM `/v1/search`)
- `web.fetch`

## Env
- `WEB_FETCH_USER_AGENT` (optional)
- `LITELLM_SEARCH_API_BASE` (optional): LiteLLM search endpoint for `search.web`.
- `LITELLM_SEARCH_API_KEY` (optional): API key for LiteLLM search (default `dummy`).

## Dependencies
- `httpx`, `trafilatura`, `readability-lxml`, `selectolax`, `mcp`

## Notes
- This tool is not exposed over HTTP; it is started by an MCP client.
- Schematron benefits from trimmed HTML; use `include_raw_html` when needed.

## Demo client
- `.venv/bin/python3 scripts/demo_client.py`
- `.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text`
- `.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3`
