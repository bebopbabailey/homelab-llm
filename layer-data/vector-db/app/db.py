from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    dbname: str


def load_db_config() -> DBConfig:
    return DBConfig(
        host=os.getenv("MEMORY_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("MEMORY_DB_PORT", "55432")),
        user=os.getenv("MEMORY_DB_USER", "memory_app"),
        password=os.getenv("MEMORY_DB_PASSWORD", "memory_app"),
        dbname=os.getenv("MEMORY_DB_NAME", "memory_main"),
    )


def dsn(cfg: DBConfig) -> str:
    return (
        f"host={cfg.host} port={cfg.port} dbname={cfg.dbname} "
        f"user={cfg.user} password={cfg.password}"
    )


def connect(cfg: DBConfig | None = None) -> psycopg.Connection[Any]:
    cfg = cfg or load_db_config()
    return psycopg.connect(dsn(cfg), autocommit=False)


def ensure_schema(conn: psycopg.Connection[Any], sql_dir: Path) -> None:
    for name in ("001_init.sql", "002_indexes.sql"):
        sql_path = sql_dir / name
        with sql_path.open("r", encoding="utf-8") as f:
            conn.execute(f.read())
    conn.commit()


def health(conn: psycopg.Connection[Any]) -> dict[str, Any]:
    row = conn.execute("SELECT now() AS db_now").fetchone()
    return {"ok": True, "db_now": row[0].isoformat() if row else None}


def fetch_stats(conn: psycopg.Connection[Any]) -> dict[str, Any]:
    docs = conn.execute("SELECT count(*) FROM memory_documents").fetchone()[0]
    chunks = conn.execute("SELECT count(*) FROM memory_chunks").fetchone()[0]
    qvec = conn.execute("SELECT count(*) FROM memory_vectors_qwen").fetchone()[0]
    mvec = conn.execute("SELECT count(*) FROM memory_vectors_mxbai").fetchone()[0]
    runs = conn.execute("SELECT count(*) FROM ingest_runs").fetchone()[0]
    return {
        "documents": docs,
        "chunks": chunks,
        "vectors_qwen": qvec,
        "vectors_mxbai": mvec,
        "ingest_runs": runs,
    }


def upsert_document(
    conn: psycopg.Connection[Any],
    payload: dict[str, Any],
) -> int:
    q = """
    INSERT INTO memory_documents (
      source, source_thread_id, source_message_id, timestamp_utc,
      title, uri, raw_ref, content_hash, metadata_json
    ) VALUES (
      %(source)s, %(source_thread_id)s, %(source_message_id)s, %(timestamp_utc)s,
      %(title)s, %(uri)s, %(raw_ref)s, %(content_hash)s, %(metadata_json)s
    )
    ON CONFLICT (source, source_thread_id, source_message_id)
    DO UPDATE SET
      title = EXCLUDED.title,
      uri = EXCLUDED.uri,
      raw_ref = EXCLUDED.raw_ref,
      content_hash = EXCLUDED.content_hash,
      metadata_json = EXCLUDED.metadata_json,
      updated_at = now()
    RETURNING doc_id
    """
    row = conn.execute(q, payload).fetchone()
    return int(row[0])


def upsert_chunk(
    conn: psycopg.Connection[Any],
    payload: dict[str, Any],
) -> int:
    q = """
    INSERT INTO memory_chunks (
      doc_id, chunk_index, text, token_estimate, text_tsv, metadata_json
    ) VALUES (
      %(doc_id)s, %(chunk_index)s, %(text)s, %(token_estimate)s,
      to_tsvector('english', %(text)s), %(metadata_json)s
    )
    ON CONFLICT (doc_id, chunk_index)
    DO UPDATE SET
      text = EXCLUDED.text,
      token_estimate = EXCLUDED.token_estimate,
      text_tsv = to_tsvector('english', EXCLUDED.text),
      metadata_json = EXCLUDED.metadata_json,
      updated_at = now()
    RETURNING chunk_id
    """
    row = conn.execute(q, payload).fetchone()
    return int(row[0])


def upsert_vector(
    conn: psycopg.Connection[Any],
    table: str,
    chunk_id: int,
    vector: list[float],
) -> None:
    if table not in {"memory_vectors_qwen", "memory_vectors_mxbai"}:
        raise ValueError(f"unsupported vector table: {table}")
    q = f"""
    INSERT INTO {table} (chunk_id, embedding)
    VALUES (%(chunk_id)s, %(embedding)s)
    ON CONFLICT (chunk_id)
    DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = now()
    """
    # pgvector accepts stringified vectors via text input format.
    emb_txt = "[" + ",".join(f"{x:.8f}" for x in vector) + "]"
    conn.execute(q, {"chunk_id": chunk_id, "embedding": emb_txt})


def delete_documents_by_source(conn: psycopg.Connection[Any], source: str) -> int:
    rows = conn.execute(
        "DELETE FROM memory_documents WHERE source = %s RETURNING doc_id",
        (source,),
    ).fetchall()
    return len(rows)


def record_ingest_run(conn: psycopg.Connection[Any], run: dict[str, Any]) -> None:
    q = """
    INSERT INTO ingest_runs (run_id, status, summary_json)
    VALUES (%(run_id)s, %(status)s, %(summary_json)s)
    ON CONFLICT (run_id)
    DO UPDATE SET status = EXCLUDED.status, summary_json = EXCLUDED.summary_json, updated_at = now()
    """
    conn.execute(q, {"run_id": run["run_id"], "status": run["status"], "summary_json": json.dumps(run)})
