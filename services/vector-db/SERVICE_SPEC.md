# Service Spec: Vector DB (Studio Main Store)

## Purpose
Provide Studio-local durable memory retrieval over personal/export corpora.

## Runtime
- Host: Studio (macOS)
- Store: Postgres 16 + pgvector
- API: FastAPI (Uvicorn)
- Management: launchd (`com.bebop.*` labels)
- Canonical source: `homelab-llm/services/vector-db`
- Current deployed target path:
  `/Users/thestudio/optillm-proxy/layer-data/vector-db`

## Launchd identity contract
- Domain: `system`
- Managed labels:
  - `com.bebop.pgvector-main`
  - `com.bebop.memory-api-main`
  - `com.bebop.memory-ingest-nightly`
  - `com.bebop.memory-backup-nightly`
- Plist paths:
  - `/Library/LaunchDaemons/com.bebop.pgvector-main.plist`
  - `/Library/LaunchDaemons/com.bebop.memory-api-main.plist`
  - `/Library/LaunchDaemons/com.bebop.memory-ingest-nightly.plist`
  - `/Library/LaunchDaemons/com.bebop.memory-backup-nightly.plist`
- Scheduling/allowlist policy:
  - `platform/ops/templates/studio_scheduling_policy.json`
  - `docs/foundation/studio-scheduling-policy.md`
- Operational wrapper for transient Studio commands:
  - `platform/ops/scripts/studio_run_utility.sh`
- Deploy sync entrypoint:
  - `services/vector-db/scripts/deploy_studio.sh`

## v1 endpoints
- `GET /health`
- `GET /v1/memory/stats`
- `POST /v1/embeddings`
- `POST /v1/memory/upsert`
- `POST /v1/memory/search`
- `POST /v1/memory/delete`

## Network bindings (v1)
- Postgres: `127.0.0.1:55432`
- Memory API: `127.0.0.1:55440`

## Backend modes
- `MEMORY_BACKEND=legacy|haystack`
- Default remains `legacy` until cutover.
- Rollback contract: set `MEMORY_BACKEND=legacy` and restart `com.bebop.memory-api-main`.

## Embedding spaces
- `qwen` space: `studio-qwen-embed-0.6b` (`Qwen/Qwen3-Embedding-0.6B`)
- `mxbai` space: `studio-mxbai-embed-large-v1` (`mixedbread-ai/mxbai-embed-large-v1`)
- Query embeddings use model-specific query prompt/prefix.
- Document embeddings are unprompted.

## Retrieval contract
- Hybrid lexical + vector retrieval.
- Haystack mode components:
  - `PgvectorKeywordRetriever`
  - `PgvectorEmbeddingRetriever`
  - `DocumentJoiner(join_mode="reciprocal_rank_fusion")`
  - `SentenceTransformersSimilarityRanker` (optional via `MEMORY_RERANK_ENABLED`)
- `model_space` is strict; no cross-space retrieval fallback.

## Data model (minimum)
- Legacy tables (unchanged):
  - `memory_documents`
  - `memory_chunks`
  - `memory_vectors_qwen`
  - `memory_vectors_mxbai`
  - `ingest_runs`
- Haystack tables (managed by `PgvectorDocumentStore`):
  - schema `memory_hs` (default)
  - table `memory_qwen` (default)
  - table `memory_mxbai` (default)

## Haystack store contract
- `embedding_dimension=1024`
- `vector_function=cosine_similarity`
- default `search_strategy=hnsw`
- fallback allowed to `exact_nearest_neighbor` via env
- `recreate_table=false`
- `create_extension=true` by default (one-time DBA bootstrap may be required)

## Ingestion contract
- Modes:
  - `MEMORY_INGEST_MODE=jsonl` (default): normalized JSONL input
  - `MEMORY_INGEST_MODE=manuals_pdf`: Haystack PDF converter/cleaner/splitter pipeline
- In both modes, writes must use deterministic `Document.id` + overwrite policy.

## Backup contract
- Daily base snapshots + WAL archival.
- Explicit restore runbook and smoke-check parity query.
