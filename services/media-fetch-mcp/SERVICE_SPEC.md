# Service Spec: media-fetch-mcp

## Purpose
Localhost-only MCP backend on the Mini for retrieval-style media and web tools.
It owns reusable search/fetch/session primitives, not answer synthesis.

## Host & Runtime
- **Host**: Mini
- **Runtime**: Python under systemd
- **Bind**: `127.0.0.1:8012`
- **MCP endpoint**: `http://127.0.0.1:8012/mcp`
- **Transport**: MCP Streamable HTTP

## Tool Surface
- `youtube.transcript`
- `media-fetch.web.search`
- `media-fetch.web.fetch`
- `media-fetch.web.session.upsert`
- `media-fetch.web.session.search`
- `media-fetch.web.session.delete`
- `media-fetch.web.quick`
- `media-fetch.web.research`

Curated local document-library ingest/search is out of scope here and belongs to
`services/docs-mcp`.

## `youtube.transcript` contract
- Input:
  - `url`
- Output:
  - `video_id`
  - `source_url`
  - `transcript_text`
  - `language`
  - `language_code`
  - `caption_type`
  - `segments[]`
    - `text`
    - `start`
    - `duration`
    - `timestamp_label`

## `media-fetch.web.search` contract
- Input:
  - `query`
  - optional `max_results` (default `5`, max `25`)
- Output:
  - `query`
  - `provider` (`searxng`)
  - `categories`
  - `results[]`
    - `title`
    - `url`
    - `snippet`
    - optional `date`
    - optional `engine`

## `media-fetch.web.fetch` contract
- Input:
  - `url`
  - optional `include_raw_html`
- Output:
  - `requested_url`
  - `final_url`
  - `canonical_url`
  - `title`
  - `clean_text`
  - `markdown`
  - `site_name`
  - `description`
  - `quality_label`
  - `quality_flags[]`
  - `extractor_used`
  - `content_sha256`
  - `content_stats`
  - optional `raw_html`

## Session contracts
- `conversation_id` is the only caller-provided session key.
- The service derives `document_id = research:<conversation_id>`.
- `media-fetch.web.session.upsert`
  - Input:
    - `conversation_id`
    - `documents[]` from `media-fetch.web.fetch`
  - Behavior:
    - chunk cleaned webpage markdown/text
    - upsert additive chunks into `vector-db`
    - stamp TTL metadata plus explicit session ids
- `media-fetch.web.session.search`
  - Input:
    - `conversation_id`
    - `query`
    - optional `profile`, `top_k`, `vector_search_mode`
  - Output:
    - chunk-level grounded evidence only
- `media-fetch.web.session.delete`
  - Input:
    - `conversation_id`
  - Behavior:
    - delete `research:<conversation_id>` from `vector-db`

## Helper-tool contracts
- `media-fetch.web.quick`
  - defaults: search `5`, fetch `3`
  - behavior: search -> fetch -> persist -> retrieve
  - output: top chunk evidence plus source/session metadata
- `media-fetch.web.research`
  - defaults: search `8`, fetch `5`
  - behavior: broader search -> broader fetch -> persist -> retrieve
  - output: broader corpus metadata plus retrieved evidence
- Neither helper performs model inference.

## Behavior
- Accept supported single-video YouTube watch, `youtu.be`, Shorts, and live
  URLs.
- Reject playlist-only, channel, search, and other non-single-video pages.
- Preserve source caption language; no translation in v1.
- Prefer the first manually created transcript YouTube exposes; otherwise use
  the first generated transcript.
- Return the full transcript always.
- Format `transcript_text` as timestamp-prefixed lines for backward
  compatibility.
- `segments[]` is the canonical machine-readable payload for downstream
  chunking/indexing.
- Apply light normalization only: collapse whitespace and skip empty/noisy
  segments.
- `media-fetch.web.search` calls local SearXNG directly instead of routing via
  LiteLLM.
- `media-fetch.web.fetch` only allows public http(s) targets and only returns
  cleaned evidence payloads for HTML/plain-text responses.
- Extraction order for webpages is `trafilatura`, then `readability-lxml`,
  then visible-text fallback.
- Session tools use `vector-db` as the only storage/retrieval backend in this
  slice.
- Session cleanup is explicit delete plus TTL metadata written on upsert.

## Error contract
Stable code-prefixed MCP tool errors:
- `invalid_url`
- `unsupported_url`
- `no_transcript`
- `upstream_failure`
- `invalid_query`
- `invalid_conversation`
- `invalid_documents`
- `url_not_allowed`
- `redirect_not_allowed`
- `redirect_limit_exceeded`
- `mime_not_allowed`
- `body_too_large`
- `parse_failed`
- `timeout`
- `config_error`

## Open WebUI posture
- Intended first client: direct Open WebUI MCP registration
- Current target registration: admin-only
- This service is localhost-only and is not part of the TinyAgents stdio
  registry in this slice.
- Open WebUI native web-search ingestion is not the canonical path for this
  service. The intended integration is direct MCP tool use.
