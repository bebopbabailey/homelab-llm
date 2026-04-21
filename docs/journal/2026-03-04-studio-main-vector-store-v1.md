# 2026-03-04 — Studio main vector store v1 scaffold (Postgres + pgvector)

## Summary
Implemented a Studio-local scaffold for the main/general memory store under
`layer-data/vector-db` with:
- Postgres + pgvector data model and indexes
- FastAPI memory service contract
- dual embedding spaces (`qwen` primary + `mxbai` fallback)
- nightly ingest + backup script templates
- launchd templates for persistent/background labels
- Studio scheduling policy manifest wiring for new owned labels

This change is scoped to Studio main-store planning/execution and does not
modify Mini web-search pipeline behavior.

## Files
- Service scaffold and docs:
  - `layer-data/vector-db/*`
  - `layer-data/vector-db/app/*`
  - `layer-data/vector-db/sql/*`
  - `layer-data/vector-db/scripts/*`
  - `layer-data/vector-db/launchd/*`
- Policy/docs:
  - `platform/ops/templates/studio_scheduling_policy.json`
  - `docs/foundation/studio-scheduling-policy.md`
  - `docs/foundation/topology.md`
  - `docs/PLATFORM_DOSSIER.md`
  - `docs/foundation/testing.md`
  - `NOW.md`
  - `BACKLOG.md`

## Contracts introduced
- Localhost-only Studio listeners (planned runtime):
  - DB: `127.0.0.1:55432`
  - API: `127.0.0.1:55440`
- API endpoints:
  - `GET /health`
  - `GET /v1/memory/stats`
  - `POST /v1/embeddings`
  - `POST /v1/memory/upsert`
  - `POST /v1/memory/search`
  - `POST /v1/memory/delete`

## Notes
- This is a scaffold implementation. Live Studio deployment/bootstrapping and
  shadow-mode quality validation remain follow-up runtime actions.
- `layer-data/vector-db/CONSTRAINTS.md` did not previously exist; it was added
  to satisfy per-service constraints requirements.
