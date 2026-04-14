CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_documents (
  doc_id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  source_thread_id TEXT NOT NULL DEFAULT '',
  source_message_id TEXT NOT NULL DEFAULT '',
  timestamp_utc TIMESTAMPTZ NULL,
  title TEXT NOT NULL DEFAULT '',
  uri TEXT NOT NULL DEFAULT '',
  raw_ref TEXT NOT NULL DEFAULT '{}',
  content_hash TEXT NOT NULL DEFAULT '',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source, source_thread_id, source_message_id)
);

CREATE TABLE IF NOT EXISTS memory_chunks (
  chunk_id BIGSERIAL PRIMARY KEY,
  doc_id BIGINT NOT NULL REFERENCES memory_documents(doc_id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  token_estimate INT NOT NULL DEFAULT 0,
  text_tsv tsvector,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (doc_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS memory_vectors_qwen (
  chunk_id BIGINT PRIMARY KEY REFERENCES memory_chunks(chunk_id) ON DELETE CASCADE,
  embedding vector(1024) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_vectors_mxbai (
  chunk_id BIGINT PRIMARY KEY REFERENCES memory_chunks(chunk_id) ON DELETE CASCADE,
  embedding vector(1024) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
