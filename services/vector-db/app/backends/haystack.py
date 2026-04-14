from __future__ import annotations

import hashlib
import logging
from typing import Any

from ..config import CFG
from ..db import connect, load_db_config
from ..embed import MODEL_MAP, default_model, fallback_model
from .base import SearchArgs

log = logging.getLogger(__name__)


class HaystackBackend:
    def __init__(self, *, warm_models: bool = True) -> None:
        try:
            from haystack import Document
            from haystack.components.embedders import (
                SentenceTransformersDocumentEmbedder,
                SentenceTransformersTextEmbedder,
            )
            from haystack.components.joiners import DocumentJoiner
            from haystack.components.rankers import SentenceTransformersSimilarityRanker
            from haystack.components.writers import DocumentWriter
            from haystack.document_stores.types import DuplicatePolicy
            from haystack.utils import Secret
            from haystack_integrations.components.retrievers.pgvector import (
                PgvectorEmbeddingRetriever,
                PgvectorKeywordRetriever,
            )
            from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Haystack backend requested but dependencies are unavailable. "
                "Install haystack-ai and pgvector-haystack."
            ) from exc

        self._Document = Document
        self._DuplicatePolicy = DuplicatePolicy
        self._DocumentWriter = DocumentWriter
        self._SentenceTransformersTextEmbedder = SentenceTransformersTextEmbedder
        self._SentenceTransformersDocumentEmbedder = SentenceTransformersDocumentEmbedder
        self._PgvectorDocumentStore = PgvectorDocumentStore
        self._PgvectorKeywordRetriever = PgvectorKeywordRetriever
        self._PgvectorEmbeddingRetriever = PgvectorEmbeddingRetriever
        self._DocumentJoiner = DocumentJoiner
        self._SentenceTransformersSimilarityRanker = SentenceTransformersSimilarityRanker
        self._Secret = Secret

        self._db_cfg = load_db_config()
        conn_str = (
            f"postgresql://{self._db_cfg.user}:{self._db_cfg.password}"
            f"@{self._db_cfg.host}:{self._db_cfg.port}/{self._db_cfg.dbname}"
        )
        self._active_search_strategy = CFG.hs_search_strategy

        self._store_qwen, self._store_mxbai = self._init_stores(conn_str)

        self._query_embedder = {
            "qwen": self._SentenceTransformersTextEmbedder(
                model=MODEL_MAP[default_model()].hf_repo,
                prefix=CFG.qwen_query_prefix,
            ),
            "mxbai": self._SentenceTransformersTextEmbedder(
                model=MODEL_MAP[fallback_model()].hf_repo,
                prefix=CFG.mxbai_query_prefix,
            ),
        }
        self._doc_embedder = {
            "qwen": self._SentenceTransformersDocumentEmbedder(model=MODEL_MAP[default_model()].hf_repo),
            "mxbai": self._SentenceTransformersDocumentEmbedder(model=MODEL_MAP[fallback_model()].hf_repo),
        }

        self._kw = {
            "qwen": self._PgvectorKeywordRetriever(document_store=self._store_qwen),
            "mxbai": self._PgvectorKeywordRetriever(document_store=self._store_mxbai),
        }
        self._vec = {
            "qwen": self._PgvectorEmbeddingRetriever(document_store=self._store_qwen),
            "mxbai": self._PgvectorEmbeddingRetriever(document_store=self._store_mxbai),
        }
        self._joiner = self._DocumentJoiner(join_mode="reciprocal_rank_fusion")
        self._ranker = None
        if CFG.rerank_enabled:
            self._ranker = self._SentenceTransformersSimilarityRanker(model=CFG.rerank_model)
        if warm_models:
            self._warm_models()

    def _warm_models(self) -> None:
        for embedder in self._query_embedder.values():
            embedder.warm_up()
        for embedder in self._doc_embedder.values():
            embedder.warm_up()
        if self._ranker is not None:
            self._ranker.warm_up()

        # Startup sanity guard to prevent dimension drift.
        for space in ("qwen", "mxbai"):
            probe = self._query_embedder[space].run(text="ping")["embedding"]
            if len(probe) != CFG.hs_embedding_dimension:
                raise RuntimeError(
                    f"embedding dimension mismatch for {space}: "
                    f"expected {CFG.hs_embedding_dimension}, got {len(probe)}"
                )

    def _init_stores(self, conn_str: str):
        search_strategy = CFG.hs_search_strategy

        def _mk(table_name: str, strategy: str):
            return self._PgvectorDocumentStore(
                connection_string=self._Secret.from_token(conn_str),
                table_name=table_name,
                schema_name=CFG.hs_schema,
                embedding_dimension=CFG.hs_embedding_dimension,
                vector_function=CFG.hs_vector_function,
                search_strategy=strategy,
                recreate_table=False,
                create_extension=CFG.hs_create_extension,
                keyword_index_name=f"{table_name}_keyword_idx",
                hnsw_index_name=f"{table_name}_hnsw_idx",
            )

        try:
            qwen = _mk(CFG.hs_table_qwen, search_strategy)
            mxbai = _mk(CFG.hs_table_mxbai, search_strategy)
            self._active_search_strategy = search_strategy
            return qwen, mxbai
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if (
                search_strategy == "hnsw"
                and CFG.hs_allow_exact_fallback
                and ("hnsw" in msg or "access method" in msg)
            ):
                log.warning(
                    "hnsw unavailable; falling back to exact_nearest_neighbor: %s",
                    exc,
                )
                qwen = _mk(CFG.hs_table_qwen, "exact_nearest_neighbor")
                mxbai = _mk(CFG.hs_table_mxbai, "exact_nearest_neighbor")
                self._active_search_strategy = "exact_nearest_neighbor"
                return qwen, mxbai
            raise

    def health(self) -> dict[str, Any]:
        # Keep DB heartbeat semantics for parity with legacy health.
        with connect(self._db_cfg) as conn:
            row = conn.execute("SELECT now()").fetchone()
        return {
            "ok": True,
            "db_now": row[0].isoformat() if row else None,
            "backend": "haystack",
            "search_strategy": self._active_search_strategy,
        }

    def _store(self, model_space: str):
        if model_space == "qwen":
            return self._store_qwen
        if model_space == "mxbai":
            return self._store_mxbai
        raise ValueError(f"unsupported model_space: {model_space}")

    def _stable_doc_id(self, d: dict[str, Any], chunk_index: int, text: str) -> str:
        token = "|".join(
            [
                str(d.get("source", "")),
                str(d.get("uri", "")),
                str(d.get("source_thread_id", "")),
                str(d.get("source_message_id", "")),
                str(chunk_index),
                str(d.get("content_hash", "")),
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
            ]
        )
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _as_haystack_docs(self, records: list[dict[str, Any]], model_space: str):
        docs = []
        for d in records:
            text = str(d.get("text", "") or "")
            chunk_index = int(d.get("chunk_index", 0))
            doc_id = self._stable_doc_id(d, chunk_index, text)
            docs.append(
                self._Document(
                    id=doc_id,
                    content=text,
                    meta={
                        "source": str(d.get("source", "unknown")),
                        "source_thread_id": str(d.get("source_thread_id", "")),
                        "source_message_id": str(d.get("source_message_id", "")),
                        "timestamp_utc": d.get("timestamp_utc"),
                        "title": str(d.get("title", "")),
                        "uri": str(d.get("uri", "")),
                        "raw_ref": d.get("raw_ref", {}),
                        "metadata": d.get("metadata", {}),
                        "chunk_index": chunk_index,
                        "token_estimate": max(1, len(text) // 4),
                        "model_space": model_space,
                    },
                )
            )
        return docs

    def _write_docs(self, docs, model_space: str) -> int:
        if not docs:
            return 0
        embedded = self._doc_embedder[model_space].run(documents=docs)["documents"]
        writer = self._DocumentWriter(
            document_store=self._store(model_space),
            policy=self._DuplicatePolicy.OVERWRITE,
        )
        result = writer.run(documents=embedded)
        return int(result.get("documents_written", 0))

    def upsert(self, documents: list[dict[str, Any]]) -> dict[str, int]:
        qdocs = self._as_haystack_docs(documents, "qwen")
        mdocs = self._as_haystack_docs(documents, "mxbai")
        qn = self._write_docs(qdocs, "qwen")
        mn = self._write_docs(mdocs, "mxbai")
        return {"documents": max(qn, mn), "chunks": max(qn, mn)}

    def _map_hit(self, idx: int, doc, model_space: str) -> dict[str, Any]:
        meta = doc.meta or {}
        score = getattr(doc, "score", 0.0) or 0.0
        return {
            "chunk_id": idx,
            "doc_id": idx,
            "chunk_index": int(meta.get("chunk_index", 0)),
            "text": str(doc.content or ""),
            "source": str(meta.get("source", "")),
            "source_thread_id": str(meta.get("source_thread_id", "")),
            "source_message_id": str(meta.get("source_message_id", "")),
            "uri": str(meta.get("uri", "")),
            "title": str(meta.get("title", "")),
            "timestamp_utc": meta.get("timestamp_utc"),
            "rrf_score": round(float(score), 8),
            "model_space": model_space,
        }

    def search(self, args: SearchArgs) -> list[dict[str, Any]]:
        space = args.model_space
        qemb = self._query_embedder[space].run(text=args.query)["embedding"]

        kw_docs = self._kw[space].run(query=args.query, top_k=max(1, args.lexical_k)).get("documents", [])
        vec_docs = self._vec[space].run(query_embedding=qemb, top_k=max(1, args.vector_k)).get("documents", [])
        joined = self._joiner.run(documents=[kw_docs, vec_docs]).get("documents", [])
        final_docs = joined

        if self._ranker is not None:
            try:
                final_docs = self._ranker.run(query=args.query, documents=joined).get("documents", joined)
            except Exception as exc:  # noqa: BLE001
                if not CFG.rerank_fail_open:
                    raise
                log.warning("rerank failed; returning fused results: %s", exc)
                final_docs = joined

        top_docs = final_docs[: max(1, args.top_k)]
        return [self._map_hit(i + 1, d, space) for i, d in enumerate(top_docs)]

    def delete(self, source: str) -> int:
        filt = {"field": "meta.source", "operator": "==", "value": source}
        q_before = int(self._store_qwen.count_documents_by_filter(filt))
        m_before = int(self._store_mxbai.count_documents_by_filter(filt))
        self._store_qwen.delete_by_filter(filt)
        self._store_mxbai.delete_by_filter(filt)
        return max(q_before, m_before)

    def stats(self) -> dict[str, Any]:
        qn = int(self._store_qwen.count_documents())
        mn = int(self._store_mxbai.count_documents())
        return {
            "documents": qn,
            "chunks": qn,
            "vectors_qwen": qn,
            "vectors_mxbai": mn,
            "ingest_runs": 0,
            "backend": "haystack",
            "search_strategy": self._active_search_strategy,
        }
