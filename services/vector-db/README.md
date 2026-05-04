# Vector DB (Studio Main Store)

Purpose: Studio-hosted durable retrieval service for long transcripts and
publication-style documents.

Status: active v1 cutover. Elasticsearch is now the primary retrieval backend.
`pgvector` remains only as a temporary rollback path behind
`MEMORY_BACKEND=legacy`.

## Ownership and deploy contract
- Canonical source of truth: this monorepo service directory.
- Current Studio runtime target: `/Users/thestudio/optillm-proxy/layer-data/vector-db`.
- Deploys sync this subtree into the existing Studio runtime path; no launchd
  path relocation is part of the current contract.

## v1 contract
- Engine: single-node Elasticsearch on Studio with one shared chunk index plus
  document and response-map metadata indexes.
- Exposure: API remains at the existing memory API surface; LAN reachability is
  an operator deployment choice, not a code-path assumption.
- Scope: YouTube transcripts, PDFs, and plain/article text with one shared
  chunk schema.
- Retrieval: lexical + vector hybrid search with explicit retrieval profiles
  (`precise`, `balanced`, `broad`).
- Embeddings: BYO local embeddings, active default
  `studio-nomic-embed-text-v1.5`.
- Follow-up state: `previous_response_id` is ergonomic only and resolves to a
  durable `document_id` mapping in the retrieval layer.

## Components
- API service: `app/main.py`
- Backend implementations: `app/backends/*`
- Service config/env parser: `app/config.py`
- Embedding loader wrappers: `app/embed.py`
- Legacy Postgres helpers: `app/db.py`, `app/retrieval.py`, `sql/*.sql`
- Batch ingest runner: `app/ingest.py`
- Retrieval/eval scripts: `scripts/eval_ir.py`, `scripts/eval_memory_quality.py`
- Studio launchd templates: `launchd/*.plist`
- Studio operational scripts: `scripts/*`

## Source-of-truth docs
- `SERVICE_SPEC.md`
- `ARCHITECTURE.md`
- `RUNBOOK.md`
- `CONSTRAINTS.md`
- `docs/vector-db-guide.md` for a practical user/operator walkthrough of the
  retrieval service, API surface, pipeline integration model, and a blunt
  explanation of how it is actually used right now versus what still belongs to
  later UX phases
- `docs/openwebui-integration-and-usage.md` for Open WebUI integration options
  and a practical explanation of how this retrieval layer fits into everyday
  use beyond YouTube transcripts
