from __future__ import annotations

from collections import defaultdict
from typing import Any

import psycopg


def _rrf(scores: dict[int, int], k: int = 60) -> dict[int, float]:
    return {doc_id: 1.0 / (k + rank) for doc_id, rank in scores.items()}


def hybrid_search(
    conn: psycopg.Connection[Any],
    *,
    query: str,
    query_vector: list[float],
    model_space: str,
    top_k: int,
    lexical_k: int,
    vector_k: int,
) -> list[dict[str, Any]]:
    table = "memory_vectors_qwen" if model_space == "qwen" else "memory_vectors_mxbai"
    vec_txt = "[" + ",".join(f"{x:.8f}" for x in query_vector) + "]"

    lexical_rows = conn.execute(
        """
        SELECT c.chunk_id, c.doc_id,
               ts_rank_cd(c.text_tsv, plainto_tsquery('english', %s)) AS score
        FROM memory_chunks c
        WHERE c.text_tsv @@ plainto_tsquery('english', %s)
        ORDER BY score DESC
        LIMIT %s
        """,
        (query, query, lexical_k),
    ).fetchall()

    vector_rows = conn.execute(
        f"""
        SELECT c.chunk_id, c.doc_id,
               1 - (v.embedding <=> %s::vector) AS score
        FROM {table} v
        JOIN memory_chunks c ON c.chunk_id = v.chunk_id
        ORDER BY v.embedding <=> %s::vector
        LIMIT %s
        """,
        (vec_txt, vec_txt, vector_k),
    ).fetchall()

    lex_rank = {int(row[0]): i + 1 for i, row in enumerate(lexical_rows)}
    vec_rank = {int(row[0]): i + 1 for i, row in enumerate(vector_rows)}

    fused: dict[int, float] = defaultdict(float)
    for cid, s in _rrf(lex_rank).items():
        fused[cid] += s
    for cid, s in _rrf(vec_rank).items():
        fused[cid] += s

    if not fused:
        return []

    chunk_ids = sorted(fused.keys(), key=lambda x: fused[x], reverse=True)[:top_k]
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.doc_id, c.chunk_index, c.text,
               d.source, d.source_thread_id, d.source_message_id, d.uri, d.title, d.timestamp_utc
        FROM memory_chunks c
        JOIN memory_documents d ON d.doc_id = c.doc_id
        WHERE c.chunk_id = ANY(%s)
        """,
        (chunk_ids,),
    ).fetchall()

    by_chunk = {int(r[0]): r for r in rows}
    out: list[dict[str, Any]] = []
    for cid in chunk_ids:
        r = by_chunk.get(cid)
        if not r:
            continue
        out.append(
            {
                "chunk_id": int(r[0]),
                "doc_id": int(r[1]),
                "chunk_index": int(r[2]),
                "text": str(r[3]),
                "source": str(r[4]),
                "source_thread_id": str(r[5] or ""),
                "source_message_id": str(r[6] or ""),
                "uri": str(r[7] or ""),
                "title": str(r[8] or ""),
                "timestamp_utc": r[9].isoformat() if r[9] else None,
                "rrf_score": round(float(fused[cid]), 8),
                "model_space": model_space,
            }
        )
    return out
