# Constraints: Vector DB (Studio Main Store)

## Hard constraints
- Engine is Postgres + pgvector for v1.
- Bindings are localhost-only for DB and API.
- Service remains Studio-local in this phase; no cross-host client wiring.
- Inference/retrieval integration is tool-mediated first (no blind auto-injection).
- Data retention is explicit snapshots + WAL archival (no implicit TTL deletion).

## Data constraints
- Message-first chunking with deterministic long-message splitting.
- Preserve provenance fields required by downstream citation and traceability.
- Never combine vectors from different embedding models in a single distance space.
- `model_space` routing is strict (`qwen` or `mxbai`), no cross-space fallback retrieval.

## Retrieval implementation constraints
- Haystack backend must use framework-native components for retrieval/fusion/rerank/filtering.
- Do not add custom retrieval SQL in Haystack mode.
- Do not add custom Haystack table/index DDL; let `PgvectorDocumentStore` manage table/index objects.
- Allowed bootstrap SQL is limited to schema existence (`CREATE SCHEMA IF NOT EXISTS ...`).

## Operational constraints
- Launchd labels must be policy-audited in
  `platform/ops/templates/studio_scheduling_policy.json`.
- All deploy/restart actions to Studio should use `platform/ops/scripts/studio_run_utility.sh`.
- Keep scripts idempotent and rollback-friendly.
