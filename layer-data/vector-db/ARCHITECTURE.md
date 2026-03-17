# Architecture: Studio Main Vector Store (v1)

## High-level flow
1. Nightly ingest job reads normalized JSONL from configured Studio-local path.
2. Records are normalized to document/chunk rows with stable provenance keys.
3. Embeddings are generated for both spaces (`qwen`, `mxbai`).
4. Lexical and vector indexes are maintained in Postgres + pgvector.
5. API serves health, upsert, search, delete, and stats endpoints.

## Why dual embedding spaces
Different embedding models map text into different latent spaces.
Distance comparisons are only meaningful within the same model space.
Therefore, v1 stores vectors in separate tables and queries one space at a time.

## Retrieval plan (hybrid)
- Lexical candidate set: Postgres FTS rank.
- Vector candidate set: cosine distance in selected vector table.
- Merge strategy: reciprocal-rank fusion (RRF) with deterministic weighting.
- Output: top-k chunk hits with provenance and score breakdown.

## Data integrity
- Provenance-first schema for traceability:
  `source`, `source_thread_id`, `source_message_id`, `timestamp`, `raw_ref`.
- Idempotent upsert keys prevent duplicate ingest on reruns.
- Ingest runs are tracked for audit/debug.

## Boundaries
- This service does not alter MLX lane behavior.
- This service does not implement Mini web-search retrieval.
- Cross-host gateway wiring is a separate phase.
