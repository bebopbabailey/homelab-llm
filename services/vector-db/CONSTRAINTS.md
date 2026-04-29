# Constraints: Vector DB (Studio Main Store)

## Hard constraints
- Elasticsearch is the primary retrieval backend for v1.
- BYO local embeddings remain the primary path; do not depend on
  `semantic_text` for v1 correctness.
- The service keeps one shared chunk index for searchable passages.
- Citation/span data must be stored on every chunk hit surface even when the
  caller does not render citations by default.
- `previous_response_id` is ergonomic only; durable follow-up state is the
  retrieval-owned `response_id -> document_id` mapping.
- `pgvector` remains only as a temporary rollback path during cutover.

## Retrieval constraints
- Do not rely on implicit `dense_vector` defaults.
- The active vector mapping must be explicit:
  - `similarity=cosine`
  - `index=true`
  - `index_options.type=int8_hnsw`
  - `m=16`
  - `ef_construction=100`
- Single-document search must benchmark exact vs approximate behavior; do not
  assume HNSW is always the right answer for small filtered corpora.
- Native Elastic RRF is version-gated; client-side RRF fallback must remain
  available.

## Operational constraints
- Launchd labels must remain policy-audited in
  `platform/ops/templates/studio_scheduling_policy.json`.
- All deploy/restart actions to Studio should use
  `platform/ops/scripts/studio_run_utility.sh`.
- Mapping/index-option changes require fresh index generations and alias swaps
  for clean evaluation.
