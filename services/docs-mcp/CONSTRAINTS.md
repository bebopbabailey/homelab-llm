# Constraints: docs-mcp

## Hard constraints
- This service is Studio-hosted and LAN-visible only on the explicit Studio LAN IP in this phase.
- This service is a separate responsibility boundary from `media-fetch-mcp`.
- `vector-db` is the only durable backing store in phase 1.
- The tool surface is limited to:
  - `docs.library.list`
  - `docs.library.ingest`
  - `docs.library.search`
  - `docs.document.search`
- The service returns evidence only. It does not synthesize answers, call models, or summarize content.

## Library constraints
- Only pre-registered libraries are allowed.
- Phase 1 registers only `library:music-manuals`.
- No arbitrary filesystem roots, no absolute path args, and no path traversal.
- Supported file types are limited to:
  - PDF
  - `.txt`
  - `.md`
  - simple `.html`
- No Office docs, no OCR, no journals/private corpora in phase 1.

## Ingest constraints
- Reingest must delete only by exact `document_id` / `document_handle`.
- Never delete by `source_type` or `library_handle` in phase 1.
- Do not index absolute filesystem paths into chunk metadata.
- Preserve page spans for PDF chunks.
- Respect safety caps:
  - `max_file_mb`
  - `max_files_per_ingest`
  - `max_chunks_per_document`

## Operational constraints
- Launchd label must remain policy-audited in `platform/ops/templates/studio_scheduling_policy.json`.
- Use `platform/ops/scripts/studio_run_utility.sh` for Studio host operations.
- Service auth is required for every MCP HTTP request.
- Remote access is limited to the Mini by the Studio pf anchor in this phase.
- No LiteLLM brokering, OWUI integration, cold storage/offload, conversation binding, or scheduled sync in this phase.
