CREATE INDEX IF NOT EXISTS idx_memory_docs_source_ts
  ON memory_documents (source, timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS idx_memory_chunks_doc
  ON memory_chunks (doc_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_memory_chunks_tsv
  ON memory_chunks USING GIN (text_tsv);

CREATE INDEX IF NOT EXISTS idx_memory_vectors_qwen_hnsw
  ON memory_vectors_qwen USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_memory_vectors_mxbai_hnsw
  ON memory_vectors_mxbai USING hnsw (embedding vector_cosine_ops);
