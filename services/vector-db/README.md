# Vector DB (Studio Main Store)

Purpose: Studio-hosted durable memory store for general-use retrieval over
personal data exports.

Status: active v1 baseline, Studio-local only, with internal `legacy|haystack`
backend selection via `MEMORY_BACKEND`.

## Ownership and deploy contract
- Canonical source of truth: this monorepo service directory.
- Current Studio runtime target: `/Users/thestudio/optillm-proxy/layer-data/vector-db`.
- Deploys sync this subtree into the existing Studio runtime path; no launchd
  path relocation is part of the current contract.

## v1 contract
- Engine: Postgres 16 + pgvector.
- Exposure: localhost only (`127.0.0.1`).
- Scope: personal/export corpus first (no web-search coupling in this service).
- Retrieval: hybrid lexical + vector.
- Internal backend mode: `legacy` or `haystack` (API contract unchanged).
- Embeddings: dual-space indexing:
  - primary: `studio-qwen-embed-0.6b`
  - fallback: `studio-mxbai-embed-large-v1`

## Components
- API service: `app/main.py`
- Backend implementations: `app/backends/*`
- Service config/env parser: `app/config.py`
- DB and schema bootstrap helpers: `app/db.py`, `sql/*.sql`
- Embedding loader wrappers: `app/embed.py`
- Legacy hybrid retrieval planner: `app/retrieval.py`
- Batch ingest runner: `app/ingest.py`
- Haystack schema bootstrap: `scripts/init_haystack_schema.py`
- Studio launchd templates: `launchd/*.plist`
- Studio operational scripts: `scripts/*`

## Source-of-truth docs
- `SERVICE_SPEC.md`
- `ARCHITECTURE.md`
- `RUNBOOK.md`
- `CONSTRAINTS.md`
