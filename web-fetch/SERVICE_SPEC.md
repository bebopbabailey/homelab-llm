# Web Fetch (MCP stdio)

## Purpose
Provide a local MCP stdio tool that fetches a URL and returns either bounded
clean text or an opt-in evidence pack for LLM consumption. `search.web` emits a
normalized `{"results":[...]}` payload and `web.fetch` performs bounded
public-web fetches with best-effort SSRF reduction and extraction metadata.

## Run
- Command: `web-fetch-mcp`
- Transport: stdio (MCP)
- Host: Mini (local only)

## Tools
- `search.web` (via LiteLLM `/v1/search`)
- `web.fetch`

## `web.fetch` output modes
- `output_mode="text"` (default): existing bounded clean-text response.
- `output_mode="evidence"`: adds structure-preserving markdown plus:
  - `canonical_url`
  - `site_name`
  - `description`
  - `links` shaped as `{text, url}`
  - `quality_label`
  - `quality_flags`
  - `content_stats`
- Evidence mode uses Trafilatura as the primary extractor. Readability is used only as rescue logic, and plain text is the last resort.

## Env
- `WEB_FETCH_USER_AGENT` (optional)
- `WEB_FETCH_MAX_BYTES` (optional)
- `WEB_FETCH_MAX_CLEAN_TEXT_CHARS` (optional)
- `WEB_FETCH_MAX_RAW_HTML_CHARS` (optional)
- `WEB_FETCH_MAX_REDIRECTS` (optional)
- `WEB_FETCH_CONNECT_TIMEOUT` / `WEB_FETCH_READ_TIMEOUT` / `WEB_FETCH_WRITE_TIMEOUT` / `WEB_FETCH_POOL_TIMEOUT` (optional)
- `WEB_FETCH_MAX_CONNECTIONS` / `WEB_FETCH_MAX_KEEPALIVE_CONNECTIONS` / `WEB_FETCH_KEEPALIVE_EXPIRY` (optional)
- `LITELLM_SEARCH_API_BASE` (optional): LiteLLM search endpoint for `search.web`.
- `LITELLM_SEARCH_API_KEY`: API key for LiteLLM search on the current Mini deployment.

## Dependencies
- `httpx`, `trafilatura`, `readability-lxml`, `selectolax`, `mcp`

## Notes
- This tool is not exposed over HTTP; it is started by an MCP client.
- The shared `httpx.Client` uses `trust_env=False`, `verify=True`, and explicit connection/pool/time limits.
- Ambient proxy and custom CA env vars are not honored by this tool.
- `web.fetch` accepts only `text/html`, `application/xhtml+xml`, and `text/plain`.
- PDFs and other binary formats are out of scope and fail as `mime_not_allowed`.
- `output_mode="evidence"` is additive; it does not change the default text-mode payload.
- Schematron benefits from trimmed HTML; use `include_raw_html` when needed for HTML/XHTML pages only.

## Demo client
- `.venv/bin/python3 scripts/demo_client.py`
- `.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text`
- `.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3`
