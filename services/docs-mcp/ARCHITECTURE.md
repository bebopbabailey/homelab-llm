# Architecture: docs-mcp

## High-level flow
1. A localhost MCP client calls one of the `docs.*` tools on Studio.
2. `docs-mcp` resolves the request against one registered library only.
3. For ingest:
   - it validates selectors and caps
   - extracts file content deterministically
   - generates deterministic `document_handle` values
   - deletes any existing exact `document_id`
   - upserts fresh chunks into `vector-db`
4. For search:
   - it calls `vector-db` search scoped by either:
     - `document_id`, or
     - `source_type + metadata.library_handle`
   - it returns evidence hits with only a thin normalization layer

## Boundaries
- `docs-mcp` owns:
  - curated library registration
  - filesystem selection and path safety
  - extraction/chunking
  - deterministic document identity
  - MCP tool surface
- `vector-db` owns:
  - durable storage
  - embeddings
  - lexical + vector retrieval
  - hit ranking
- `media-fetch-mcp` remains separate and read-only for source/media acquisition.

## Determinism choices
- One registered library in phase 1: `library:music-manuals`
- One acceptance fixture in phase 1: `reface_en_om_b0.pdf`
- Reingest deletes by exact `document_id` only.
- Source URIs use logical library handles, not absolute paths.

## Out of scope
- Answer synthesis
- LiteLLM brokering
- OWUI integration
- Conversation bindings
- Arbitrary uploads
- Background watchers or scheduled sync
- Cold storage/offload
