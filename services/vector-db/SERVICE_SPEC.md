# Service Spec: Vector DB (Studio Main Store)

## Purpose
Provide durable retrieval over long transcripts and publication-style documents
through the existing memory API contract.

## Runtime
- Host: Studio (macOS)
- Primary store: Elasticsearch, single-node, pinned to `9.3.3`
  (`darwin-aarch64`) with a minimum supported floor of `8.19.x`
- API: FastAPI (Uvicorn)
- Management: launchd (`com.bebop.*` labels)
- Canonical source: `homelab-llm/services/vector-db`
- Current deployed target path:
  `/Users/thestudio/optillm-proxy/layer-data/vector-db`

## Launchd identity contract
- Domain: `system`
- Managed labels:
  - `com.bebop.elasticsearch-memory-main`
  - `com.bebop.kibana-memory-main`
  - `com.bebop.memory-api-main`
  - `com.bebop.memory-ingest-nightly`
  - `com.bebop.memory-backup-nightly`
- Plist paths:
  - `/Library/LaunchDaemons/com.bebop.elasticsearch-memory-main.plist`
  - `/Library/LaunchDaemons/com.bebop.kibana-memory-main.plist`
  - `/Library/LaunchDaemons/com.bebop.memory-api-main.plist`
  - `/Library/LaunchDaemons/com.bebop.memory-ingest-nightly.plist`
  - `/Library/LaunchDaemons/com.bebop.memory-backup-nightly.plist`

## Endpoints
- `GET /health`
- `GET /v1/memory/stats`
- `POST /v1/embeddings`
- `POST /v1/memory/upsert`
- `POST /v1/memory/search`
- `POST /v1/memory/delete`
- `POST /v1/memory/response-map/upsert`
- `POST /v1/memory/response-map/resolve`

## Network bindings
- Existing public API contract remains `55440`.
- Elasticsearch is localhost-only on `127.0.0.1:9200`.
- Kibana is localhost-only on `127.0.0.1:5601`.
- The Studio memory API binds to `0.0.0.0:55440`.
- Studio-local callers should prefer `http://127.0.0.1:55440`.
- v1 firewall posture allows Mini `192.168.1.71` only; broader LAN access is
  blocked.
- Write routes require the bearer token from
  `MEMORY_API_WRITE_BEARER_TOKEN_FILE`; read/search routes remain open on the
  Mini-only LAN path.

## Backend modes
- `MEMORY_BACKEND=elastic|legacy|haystack`
- Default: `elastic`
- `legacy` remains a temporary rollback path to Postgres + pgvector.
- `haystack` remains available for the old pgvector/Haystack experiments but is
  no longer the primary target.

## Embeddings
- Public embedding endpoint remains `POST /v1/embeddings`.
- `POST /v1/embeddings` accepts an optional `prefix` field for OWUI native
  Knowledge compatibility:
  - `search_query:` -> query embedding path
  - `search_document:` -> document embedding path
  - other non-empty prefixes -> deterministic raw-prefix fallback
- Internal batching controls:
  - `MEMORY_EMBED_BATCH_SIZE` for raw embeddings
  - `MEMORY_EMBED_QUERY_BATCH_SIZE` for query embeddings
  - `MEMORY_EMBED_DOCUMENT_BATCH_SIZE` for document embeddings
  - Studio phase-1 manuals/doc ingestion uses `MEMORY_EMBED_DOCUMENT_BATCH_SIZE=1`
    for reliability with the current Nomic runtime
- Active embedding default:
  - `studio-nomic-embed-text-v1.5`
  - repo default source: `nomic-ai/nomic-embed-text-v1.5`
- Legacy model entries remain available in the local registry for rollback and
  comparison:
  - `studio-qwen-embed-0.6b`
  - `studio-mxbai-embed-large-v1`
- Elastic v1 uses one active embedding space per deployed index generation.

## Elastic index contract
- Shared read alias: `memory-chunks-current`
- Physical chunk index shape:
  - `memory-chunks-v1-<model>-d<dims>-<index_type>`
- Additional indexes:
  - `memory-documents-v1`
  - `memory-response-map-v1`
- Chunk mapping requirements:
  - `dense_vector`
  - `similarity=cosine`
  - `dims` resolved from the active embedding model
  - `index=true`
  - `index_options.type=int8_hnsw`
  - `index_options.m=16`
  - `index_options.ef_construction=100`
- Span fields are stored on every chunk:
  - transcripts: `timestamp_label`, `start_ms`, `end_ms`
  - publications: `page_start`, `page_end`
  - optional offsets: `char_start`, `char_end`

## Retrieval contract
- Profiles:
  - `precise`: lexical 24, vector 24, candidates 96, final 8, citations on
  - `balanced`: lexical 48, vector 48, candidates 192, final 10, citations off
  - `broad`: lexical 96, vector 96, candidates 384, final 14, citations off
- Filters:
  - `document_id`
  - `source_type` / `source_types`
  - metadata term/terms filters
- Single-document routing:
  - exact brute-force vector search for documents at or below
    `MEMORY_SINGLE_DOC_EXACT_MAX_CHUNKS` (default `1024`)
  - filtered approximate kNN otherwise
- Hybrid fusion:
  - native Elastic RRF only when the runtime supports retrievers and the
    service enables it
  - deterministic client-side RRF fallback otherwise
- Citation/spans are always available internally on hits, but not rendered by
  default outside the `precise` profile or an explicit caller override.

## Durable follow-up contract
- `memory-response-map-v1` stores:
  - public `response_id`
  - `document_id`
  - `source_type`
  - `summary_mode`
  - `created_at`
- Callers may still supply `previous_response_id`, but retrieval-backed flows
  must resolve that identifier into a durable `document_id` before searching.

## Ingestion contract
- `POST /v1/memory/upsert` remains additive:
  - old single-text payloads still work
  - preferred path uses explicit `document_id`, `source_type`, and `chunks[]`
- v1 source coverage:
  - YouTube transcripts
  - PDFs
  - plain/article text
- `content-extract` is optional and only justified when deterministic
  extraction/normalization materially helps document ingest.

## Operational checks
- `/health` must verify Elastic connectivity and report backend/version/license.
- `/v1/memory/stats` must report:
  - active backend
  - index alias + physical chunk index
  - doc count
  - chunk count
  - response-map count
  - embedding model
  - embedding dims
  - vector index type
  - HNSW params
  - exact-search cutoff
  - retriever mode
- Snapshot repository:
  - `path.repo` is pinned to the repo-managed Studio runtime tree
  - repository name defaults to `memory-main-repo`
  - manual snapshots are part of the supported operator contract

## Reindex contract
- Mapping or embedding changes require a new physical index generation.
- Alias swaps are the clean promotion path.
- Changing HNSW `index_options` alone does not retroactively rebuild old
  vectors; clean evaluation requires reindexing or re-embedding into a fresh
  index generation.
