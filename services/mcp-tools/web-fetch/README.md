# Web Fetch (MCP stdio tool)

## Purpose
Fetch a URL and return either cleaned, model-ready text or an opt-in evidence
pack for downstream use in search, summarization, or schema extraction.

## Status
Implemented (stdio MCP tool). `search.web` normalizes upstream search payloads to
`{"results":[...]}` and `web.fetch` performs bounded public-web fetches with
best-effort SSRF reduction, HTML/text-only MIME policy, and extraction metadata.
Runs locally via an MCP client; not a systemd service.

## Tools exposed
- `search.web` (via LiteLLM `/v1/search`)
- `web.fetch`

## `web.fetch` modes
- Default `output_mode="text"` preserves the existing bounded clean-text contract.
- Optional `output_mode="evidence"` adds:
  - `markdown`
  - `canonical_url`
  - `site_name`
  - `description`
  - `links` shaped as `{text, url}`
  - `quality_label`
  - `quality_flags`
  - `content_stats`
- Evidence mode keeps Trafilatura as the primary extractor. Readability is rescue-only, and visible text remains the final fallback.

## Run (dev)
```bash
cd /home/christopherbailey/homelab-llm/services/mcp-tools/web-fetch
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
- `WEB_FETCH_USER_AGENT` (optional): override the default `User-Agent`.
- `WEB_FETCH_MAX_BYTES` (optional): fetch body cap in bytes.
- `WEB_FETCH_MAX_CLEAN_TEXT_CHARS` (optional): cap for returned `clean_text`.
- `WEB_FETCH_MAX_RAW_HTML_CHARS` (optional): cap for returned `raw_html`.
- `WEB_FETCH_MAX_REDIRECTS` (optional): redirect hop cap.
- `WEB_FETCH_CONNECT_TIMEOUT`, `WEB_FETCH_READ_TIMEOUT`, `WEB_FETCH_WRITE_TIMEOUT`, `WEB_FETCH_POOL_TIMEOUT` (optional): timeout controls.
- `WEB_FETCH_MAX_CONNECTIONS`, `WEB_FETCH_MAX_KEEPALIVE_CONNECTIONS`, `WEB_FETCH_KEEPALIVE_EXPIRY` (optional): shared HTTP client limits.
- `LITELLM_SEARCH_API_BASE` (optional): LiteLLM search endpoint for `search.web`.
- `LITELLM_SEARCH_API_KEY`: API key for LiteLLM search on the current Mini deployment.

## Network policy
- Fetches use a shared `httpx.Client` with `trust_env=False` and `verify=True`.
- Ambient proxy and custom CA env vars are not honored in this tool.
- `web.fetch` only accepts `text/html`, `application/xhtml+xml`, and `text/plain`.
- PDFs and other binary formats are rejected as `mime_not_allowed`.

## Tool Contract
See `docs/foundation/tool-contracts.md` (`web.fetch`).
