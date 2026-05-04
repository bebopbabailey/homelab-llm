# Service Spec: docs-mcp

## Purpose
Provide a stable MCP surface for ingesting and searching curated local document libraries on Studio, backed by the existing `vector-db` service.

## Runtime
- Host: Studio (macOS)
- Transport: MCP Streamable HTTP
- Bind: `192.168.1.72:8013`
- Management: launchd (`com.bebop.docs-mcp-main`)
- Canonical source: `homelab-llm/services/docs-mcp`
- Current deployed target path:
  `/Users/thestudio/optillm-proxy/layer-tools/docs-mcp`

## Exposure
- Audience: internal service/tool callers only
- Canonical MCP endpoint: `http://192.168.1.72:8013/mcp`
- HTTP auth: required bearer token on every request
- Network policy: Studio pf anchor allows Mini `192.168.1.71` plus Studio self-access only
- `vector-db` remains Studio-local behind this facade

## Launchd identity contract
- Domain: `system`
- Managed label:
  - `com.bebop.docs-mcp-main`
- Plist path:
  - `/Library/LaunchDaemons/com.bebop.docs-mcp-main.plist`

## MCP tool surface
- `docs.library.list`
- `docs.library.ingest`
- `docs.library.search`
- `docs.document.search`

## Local helper
- Repo helper script:
  - `services/docs-mcp/scripts/manual_lookup.py`
- Purpose:
  - one-command read-only wrapper around the current lookup/search MCP tools
    for the music-manuals workflow
- Status:
  - `list`, `search-document`, and `search-library` are supported
  - `ingest` is explicitly parked as under construction; use a real MCP client
    for authoritative ingest

## Registered libraries (phase 1)
- `library:music-manuals`
  - `library_id`: `music-manuals`
  - `source_type`: `manual`
  - root path: `/Users/thestudio/Documents/music-manuals`

## Config/env
- `DOCS_MCP_VECTOR_DB_BASE`
- `DOCS_MCP_VECTOR_DB_WRITE_TOKEN`
- `DOCS_MCP_VECTOR_DB_WRITE_TOKEN_FILE`
- `DOCS_MCP_BEARER_TOKEN`
- `DOCS_MCP_BEARER_TOKEN_FILE`
- `DOCS_MCP_LIBRARY_MUSIC_MANUALS_ROOT`
- `DOCS_MCP_MAX_FILE_MB`
- `DOCS_MCP_MAX_FILES_PER_INGEST`
- `DOCS_MCP_MAX_CHUNKS_PER_DOCUMENT`
- `DOCS_MCP_CHUNK_TARGET_CHARS`
- `DOCS_MCP_CHUNK_OVERLAP_CHARS`

Preferred Studio runtime values:
- `DOCS_MCP_VECTOR_DB_BASE=http://127.0.0.1:55440`
- `DOCS_MCP_VECTOR_DB_WRITE_TOKEN_FILE=/Users/thestudio/data/memory-main/secrets/memory-api-write-token`
- `DOCS_MCP_BEARER_TOKEN_FILE=/Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token`
- `DOCS_MCP_LIBRARY_MUSIC_MANUALS_ROOT=/Users/thestudio/Documents/music-manuals`
- `DOCS_MCP_CHUNK_TARGET_CHARS=300`
- `DOCS_MCP_CHUNK_OVERLAP_CHARS=40`

## Ingest contract
- `docs.library.ingest` accepts only:
  - `library_id`, or
  - `library_handle`
- Optional narrow selectors:
  - `document_handle`
  - `relative_path`
- `dry_run=true` performs no `vector-db` writes and returns:
  - `matched_files`
  - `would_index`
  - `would_skip`
  - `document_handle_previews`
  - `errors`
- Normal ingest returns:
  - `library_handle`
  - `document_handles`
  - `documents_indexed`
  - `chunks_indexed`
  - `skipped_files`
  - `errors`
  - `ingest_run_id`

## Search contract
- `docs.library.search` requires one explicit library selector plus `query`.
- `docs.document.search` requires one explicit `document_handle` plus `query`.
- Both return evidence only:
  - `document_id`
  - `document_handle`
  - `title`
  - `text`
  - `spans`
  - `score`
  - `rank`

## Storage contract
- Uses existing `vector-db` endpoints only:
  - `POST /v1/memory/upsert`
  - `POST /v1/memory/search`
  - `POST /v1/memory/delete`
- Deterministic document handle format:
  - `manual:music-manuals:<document-slug>`
- Metadata persisted with each document/chunk:
  - `library_id`
  - `library_handle`
  - `document_handle`
  - `relative_path`
  - `content_hash`
  - `ingest_run_id`
- Source URI format:
  - `file://library:music-manuals/<relative_path>`
- Absolute filesystem roots stay in service config/operator docs only.

## PDF extraction contract
- Extractor: `pypdf` with `cryptography` installed for AES-encrypted PDFs.
- Page handling:
  - extraction occurs page-by-page
  - chunk spans preserve `page_start` and `page_end`
  - page-local chunks also carry `char_start` / `char_end` within the page text window

## Phase-1 acceptance target
- Exact fixture file:
  - `/Users/thestudio/Documents/music-manuals/reface_en_om_b0.pdf`
- Acceptance requires:
  - targeted ingest of that manual
  - deterministic document handle generation
  - retrieval of at least one relevant chunk with `page_start` and `page_end` present
