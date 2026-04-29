# NOW

Active
- Cut over `services/vector-db` to Elastic-backed retrieval with explicit HNSW
  mappings, durable `response_id -> document_id` state, and retrieval-backed
  follow-up grounding for long-form YouTube/publication content.

NEXT UP
- Validate the new Elastic backend against the retrieval/eval gates and decide
  when to retire the temporary pgvector rollback path.
