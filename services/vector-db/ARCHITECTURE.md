# Architecture: Studio Main Retrieval Store (v1)

## High-level flow
1. A caller or helper script normalizes source content into explicit chunks with
   provenance and span data.
2. The service generates local embeddings with the active model.
3. Documents and chunks are written into Elasticsearch:
   - shared chunk index
   - document metadata index
   - response-map index
4. Search runs a lexical branch plus a vector branch, then fuses the results
   through native or client-side RRF.
5. Long-form clients reuse a public `response_id`, which the retrieval layer
   resolves into a durable `document_id` before searching.

## Shared chunk schema
- `document_id`
- `chunk_id`
- `source_type`
- `text`
- `title`
- `source_uri`
- `section_title`
- transcript spans: `timestamp_label`, `start_ms`, `end_ms`
- publication spans: `page_start`, `page_end`
- optional offsets: `char_start`, `char_end`
- filterable `metadata`
- `dense_vector` embedding

## Retrieval plan
- Lexical branch: BM25-style text search over `text`, `title`, and
  `section_title`.
- Vector branch:
  - exact `script_score` cosine search for small single-document scopes
  - filtered HNSW kNN for larger scopes
- Fusion:
  - native Elastic retriever-tree RRF when available and enabled
  - deterministic client-side RRF otherwise
- Output: top chunk hits with provenance and stored spans. Citation rendering is
  a caller choice, not a storage concern.

## Versioned HNSW discipline
- The active chunk index is versioned by embedding model, dims, and index type.
- v1 explicit mapping baseline:
  - `similarity=cosine`
  - `index=true`
  - `index_options.type=int8_hnsw`
  - `m=16`
  - `ef_construction=100`
- Mapping/index-option changes are evaluated on fresh physical indexes and
  promoted via alias swap.

## Boundaries
- This service owns retrieval durability, embedding generation, and response-id
  document mapping.
- This service also provides the OpenAI-compatible embedding surface used by
  Open WebUI native Knowledge. Query/document prefix mode is selected through
  the optional `prefix` field on `POST /v1/embeddings`.
- This service does not own model inference.
- LiteLLM or other gateways may use it as a retrieval backend, but they should
  not treat provider conversation state as the durable memory layer.

## Operator visibility
- Elasticsearch remains localhost-only on Studio.
- Kibana is the operator GUI, also localhost-only on Studio.
- Open WebUI does not use Kibana in the user path; it uses direct Elasticsearch
  storage/query access through a Mini-local bridge and `vector-db` only for
  embeddings.
