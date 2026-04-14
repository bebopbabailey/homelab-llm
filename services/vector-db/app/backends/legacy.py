from __future__ import annotations

import json
from typing import Any

from ..db import (
    connect,
    delete_documents_by_source,
    fetch_stats,
    health,
    load_db_config,
    upsert_chunk,
    upsert_document,
    upsert_vector,
)
from ..embed import EmbeddingRegistry, fallback_model
from ..retrieval import hybrid_search
from .base import SearchArgs


class LegacyBackend:
    def __init__(self) -> None:
        self._db_cfg = load_db_config()
        self._embed = EmbeddingRegistry()

    def health(self) -> dict[str, Any]:
        with connect(self._db_cfg) as conn:
            return health(conn)

    def stats(self) -> dict[str, Any]:
        with connect(self._db_cfg) as conn:
            stats = fetch_stats(conn)
        stats["backend"] = "legacy"
        return stats

    def upsert(self, documents: list[dict[str, Any]]) -> dict[str, int]:
        docs = 0
        chunks = 0
        with connect(self._db_cfg) as conn:
            for d in documents:
                text = str(d.get("text", "") or "")
                doc_payload = {
                    "source": str(d.get("source", "unknown")),
                    "source_thread_id": str(d.get("source_thread_id", "")),
                    "source_message_id": str(d.get("source_message_id", "")),
                    "timestamp_utc": d.get("timestamp_utc"),
                    "title": str(d.get("title", "")),
                    "uri": str(d.get("uri", "")),
                    "raw_ref": json.dumps(d.get("raw_ref", {})),
                    "content_hash": str(d.get("content_hash", "")),
                    "metadata_json": json.dumps(d.get("metadata", {})),
                }
                doc_id = upsert_document(conn, doc_payload)
                chunk_id = upsert_chunk(
                    conn,
                    {
                        "doc_id": doc_id,
                        "chunk_index": int(d.get("chunk_index", 0)),
                        "text": text,
                        "token_estimate": max(1, len(text) // 4),
                        "metadata_json": json.dumps({"upsert": True, **d.get("chunk_meta", {})}),
                    },
                )
                qvec = self._embed.embed("studio-qwen-embed-0.6b", [text])[0]
                mvec = self._embed.embed(fallback_model(), [text])[0]
                upsert_vector(conn, "memory_vectors_qwen", chunk_id, qvec)
                upsert_vector(conn, "memory_vectors_mxbai", chunk_id, mvec)
                docs += 1
                chunks += 1
            conn.commit()
        return {"documents": docs, "chunks": chunks}

    def search(self, args: SearchArgs) -> list[dict[str, Any]]:
        model_name = "studio-qwen-embed-0.6b" if args.model_space == "qwen" else fallback_model()
        qv = self._embed.embed(model_name, [args.query])[0]
        with connect(self._db_cfg) as conn:
            return hybrid_search(
                conn,
                query=args.query,
                query_vector=qv,
                model_space=args.model_space,
                top_k=max(1, args.top_k),
                lexical_k=max(1, args.lexical_k),
                vector_k=max(1, args.vector_k),
            )

    def delete(self, source: str) -> int:
        with connect(self._db_cfg) as conn:
            n = delete_documents_by_source(conn, source)
            conn.commit()
        return n
