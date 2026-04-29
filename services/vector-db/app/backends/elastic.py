from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from ..config import CFG
from ..embed import EmbeddingRegistry, default_model
from .base import SearchArgs

log = logging.getLogger(__name__)


def _parse_version(raw: str) -> tuple[int, int, int]:
    parts = (raw or "0.0.0").split(".")
    out = []
    for part in parts[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits or "0"))
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


def _version_gte(lhs: str, rhs: str) -> bool:
    return _parse_version(lhs) >= _parse_version(rhs)


def _slugify_model(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def _hash_token(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ElasticBackend:
    def __init__(self) -> None:
        try:
            from elasticsearch import Elasticsearch
            from elasticsearch.helpers import bulk
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Elastic backend requested but dependencies are unavailable. "
                "Install elasticsearch>=9.2.0,<10."
            ) from exc

        client_kwargs: dict[str, Any] = {
            "hosts": [CFG.elastic_url],
            "verify_certs": CFG.elastic_verify_certs,
            "request_timeout": CFG.elastic_request_timeout_seconds,
        }
        if CFG.elastic_api_key:
            client_kwargs["api_key"] = CFG.elastic_api_key
        elif CFG.elastic_username and CFG.elastic_password:
            client_kwargs["basic_auth"] = (CFG.elastic_username, CFG.elastic_password)

        self._client = Elasticsearch(**client_kwargs)
        self._bulk = bulk
        self._embed = EmbeddingRegistry()
        self._model_name = default_model()
        self._model_info = self._embed.model_info(self._model_name)
        self._dims = len(self._embed.embed_document(self._model_name, ["ping"])[0])
        expected_dims = int(self._model_info["default_dimension"])
        if self._dims != expected_dims:
            raise RuntimeError(
                f"embedding dimension mismatch for {self._model_name}: "
                f"expected {expected_dims}, got {self._dims}"
            )

        info = self._client.info()
        version = str(info.get("version", {}).get("number", "0.0.0"))
        if not _version_gte(version, CFG.elastic_min_supported_version):
            raise RuntimeError(
                f"unsupported elasticsearch version {version}; "
                f"minimum supported is {CFG.elastic_min_supported_version}"
            )
        self._cluster_version = version
        self._license = self._fetch_license()
        self._supports_retriever_api = _version_gte(version, "8.14.0")
        self._native_rrf_enabled = bool(CFG.elastic_enable_native_rrf and self._supports_retriever_api)
        self._physical_chunks_index = (
            f"memory-chunks-v1-{_slugify_model(self._model_name)}-d{self._dims}-{CFG.elastic_index_type}"
        )
        self._ensure_indices()

    def _fetch_license(self) -> dict[str, Any]:
        try:
            return self._client.perform_request("GET", "/_license").body
        except Exception as exc:  # noqa: BLE001
            log.warning("elastic license probe failed: %s", exc)
            return {"license": {"type": "unknown", "status": "unknown"}}

    def _ensure_indices(self) -> None:
        if not self._client.indices.exists(index=self._physical_chunks_index):
            self._client.indices.create(index=self._physical_chunks_index, mappings=self._chunk_mappings())
        if not self._client.indices.exists_alias(name=CFG.elastic_chunks_alias):
            self._client.indices.put_alias(index=self._physical_chunks_index, name=CFG.elastic_chunks_alias)
        if not self._client.indices.exists(index=CFG.elastic_documents_index):
            self._client.indices.create(index=CFG.elastic_documents_index, mappings=self._document_mappings())
        if not self._client.indices.exists(index=CFG.elastic_response_map_index):
            self._client.indices.create(index=CFG.elastic_response_map_index, mappings=self._response_map_mappings())

    def _chunk_mappings(self) -> dict[str, Any]:
        return {
            "dynamic": False,
            "properties": {
                "document_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "source": {"type": "keyword"},
                "source_thread_id": {"type": "keyword"},
                "source_message_id": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 512}}},
                "source_uri": {"type": "keyword"},
                "section_title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 512}}},
                "text": {"type": "text"},
                "chunk_index": {"type": "integer"},
                "token_estimate": {"type": "integer"},
                "timestamp_utc": {"type": "date", "ignore_malformed": True},
                "timestamp_label": {"type": "keyword"},
                "start_ms": {"type": "long"},
                "end_ms": {"type": "long"},
                "page_start": {"type": "integer"},
                "page_end": {"type": "integer"},
                "char_start": {"type": "integer"},
                "char_end": {"type": "integer"},
                "embedding_model": {"type": "keyword"},
                "metadata": {"type": "object", "enabled": True},
                "embedding": {
                    "type": "dense_vector",
                    "dims": self._dims,
                    "similarity": CFG.elastic_similarity,
                    "index": True,
                    "index_options": {
                        "type": CFG.elastic_index_type,
                        "m": CFG.elastic_hnsw_m,
                        "ef_construction": CFG.elastic_hnsw_ef_construction,
                    },
                },
            },
        }

    def _document_mappings(self) -> dict[str, Any]:
        return {
            "dynamic": False,
            "properties": {
                "document_id": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "source": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 512}}},
                "source_uri": {"type": "keyword"},
                "source_thread_id": {"type": "keyword"},
                "source_message_id": {"type": "keyword"},
                "timestamp_utc": {"type": "date", "ignore_malformed": True},
                "chunk_count": {"type": "integer"},
                "embedding_model": {"type": "keyword"},
                "embedding_dims": {"type": "integer"},
                "summary_mode": {"type": "keyword"},
                "summary_text": {"type": "text"},
                "ingest_status": {"type": "keyword"},
                "metadata": {"type": "object", "enabled": True},
                "updated_at": {"type": "date"},
            },
        }

    def _response_map_mappings(self) -> dict[str, Any]:
        return {
            "dynamic": False,
            "properties": {
                "response_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "summary_mode": {"type": "keyword"},
                "created_at": {"type": "date"},
            },
        }

    def _normalize_documents(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for raw in documents:
            document_id = str(raw.get("document_id") or "").strip()
            source = str(raw.get("source", "unknown"))
            source_type = str(raw.get("source_type") or source or "generic")
            source_thread_id = str(raw.get("source_thread_id", ""))
            source_message_id = str(raw.get("source_message_id", ""))
            title = str(raw.get("title", ""))
            uri = str(raw.get("uri", ""))
            timestamp_utc = raw.get("timestamp_utc")
            metadata = dict(raw.get("metadata", {}) or {})
            raw_ref = dict(raw.get("raw_ref", {}) or {})
            chunks = raw.get("chunks")
            if not isinstance(chunks, list) or not chunks:
                text = str(raw.get("text", "") or "")
                chunks = [
                    {
                        "chunk_id": raw.get("chunk_id"),
                        "chunk_index": int(raw.get("chunk_index", 0)),
                        "text": text,
                        "metadata": dict(raw.get("chunk_meta", {}) or {}),
                    }
                ]
            if not document_id:
                document_id = _hash_token(source, source_thread_id, source_message_id or title or uri)
            normalized_chunks: list[dict[str, Any]] = []
            for idx, chunk in enumerate(chunks):
                if not isinstance(chunk, dict):
                    continue
                text = str(chunk.get("text", "") or "")
                chunk_index = int(chunk.get("chunk_index", idx))
                chunk_id = str(chunk.get("chunk_id") or "").strip() or _hash_token(document_id, str(chunk_index), text[:120])
                chunk_metadata = dict(chunk.get("metadata", {}) or {})
                normalized_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_index,
                        "text": text,
                        "token_estimate": max(1, len(text) // 4),
                        "section_title": str(chunk.get("section_title", "")),
                        "timestamp_label": str(chunk.get("timestamp_label", "")),
                        "start_ms": _safe_int(chunk.get("start_ms")),
                        "end_ms": _safe_int(chunk.get("end_ms")),
                        "page_start": _safe_int(chunk.get("page_start")),
                        "page_end": _safe_int(chunk.get("page_end")),
                        "char_start": _safe_int(chunk.get("char_start")),
                        "char_end": _safe_int(chunk.get("char_end")),
                        "metadata": chunk_metadata,
                    }
                )
            normalized.append(
                {
                    "document_id": document_id,
                    "source_type": source_type,
                    "source": source,
                    "source_thread_id": source_thread_id,
                    "source_message_id": source_message_id,
                    "title": title,
                    "source_uri": uri,
                    "timestamp_utc": timestamp_utc,
                    "metadata": {**metadata, "raw_ref": raw_ref},
                    "chunks": normalized_chunks,
                }
            )
        return normalized

    def health(self) -> dict[str, Any]:
        info = self._client.info()
        cluster = str(info.get("cluster_name", ""))
        return {
            "ok": True,
            "backend": "elastic",
            "cluster_name": cluster,
            "elastic_url": CFG.elastic_url,
            "elastic_version": self._cluster_version,
            "elastic_license": self._license.get("license", {}),
            "native_rrf_capable": self._supports_retriever_api,
            "native_rrf_enabled": self._native_rrf_enabled,
            "embedding_model": self._model_name,
            "embedding_dims": self._dims,
            "embedding_prefix_mode": self._model_info["prefix_mode"],
        }

    def stats(self) -> dict[str, Any]:
        chunks = int(self._client.count(index=CFG.elastic_chunks_alias).get("count", 0))
        documents = int(self._client.count(index=CFG.elastic_documents_index).get("count", 0))
        response_maps = int(self._client.count(index=CFG.elastic_response_map_index).get("count", 0))
        return {
            "backend": "elastic",
            "elastic_url": CFG.elastic_url,
            "elastic_version": self._cluster_version,
            "elastic_license": self._license.get("license", {}),
            "index_alias": CFG.elastic_chunks_alias,
            "index_name": self._physical_chunks_index,
            "document_index_name": CFG.elastic_documents_index,
            "response_map_index_name": CFG.elastic_response_map_index,
            "documents": documents,
            "chunks": chunks,
            "response_maps": response_maps,
            "embedding_model": self._model_name,
            "embedding_dims": self._dims,
            "embedding_query_prefix": self._model_info["query_prefix"],
            "embedding_document_prefix": self._model_info["document_prefix"],
            "embedding_prefix_mode": self._model_info["prefix_mode"],
            "vector_index_type": CFG.elastic_index_type,
            "hnsw_m": CFG.elastic_hnsw_m,
            "hnsw_ef_construction": CFG.elastic_hnsw_ef_construction,
            "single_doc_exact_max_chunks": CFG.elastic_single_doc_exact_max_chunks,
            "native_rrf_capable": self._supports_retriever_api,
            "native_rrf_enabled": self._native_rrf_enabled,
            "retriever_mode": "native_rrf" if self._native_rrf_enabled else "client_rrf",
        }

    def upsert(self, documents: list[dict[str, Any]]) -> dict[str, int]:
        normalized = self._normalize_documents(documents)
        chunk_texts = [chunk["text"] for doc in normalized for chunk in doc["chunks"]]
        vectors = self._embed.embed_document(self._model_name, chunk_texts) if chunk_texts else []
        vec_iter = iter(vectors)

        actions: list[dict[str, Any]] = []
        chunk_count = 0
        for doc in normalized:
            actions.append(
                {
                    "_op_type": "index",
                    "_index": CFG.elastic_documents_index,
                    "_id": doc["document_id"],
                    "_source": {
                        "document_id": doc["document_id"],
                        "source_type": doc["source_type"],
                        "source": doc["source"],
                        "title": doc["title"],
                        "source_uri": doc["source_uri"],
                        "source_thread_id": doc["source_thread_id"],
                        "source_message_id": doc["source_message_id"],
                        "timestamp_utc": doc["timestamp_utc"],
                        "chunk_count": len(doc["chunks"]),
                        "embedding_model": self._model_name,
                        "embedding_dims": self._dims,
                        "ingest_status": "indexed",
                        "metadata": doc["metadata"],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                }
            )
            for chunk in doc["chunks"]:
                vector = next(vec_iter)
                actions.append(
                    {
                        "_op_type": "index",
                        "_index": CFG.elastic_chunks_alias,
                        "_id": chunk["chunk_id"],
                        "_source": {
                            "document_id": doc["document_id"],
                            "chunk_id": chunk["chunk_id"],
                            "source_type": doc["source_type"],
                            "source": doc["source"],
                            "source_thread_id": doc["source_thread_id"],
                            "source_message_id": doc["source_message_id"],
                            "title": doc["title"],
                            "source_uri": doc["source_uri"],
                            "section_title": chunk["section_title"],
                            "text": chunk["text"],
                            "chunk_index": chunk["chunk_index"],
                            "token_estimate": chunk["token_estimate"],
                            "timestamp_utc": doc["timestamp_utc"],
                            "timestamp_label": chunk["timestamp_label"],
                            "start_ms": chunk["start_ms"],
                            "end_ms": chunk["end_ms"],
                            "page_start": chunk["page_start"],
                            "page_end": chunk["page_end"],
                            "char_start": chunk["char_start"],
                            "char_end": chunk["char_end"],
                            "embedding_model": self._model_name,
                            "metadata": {**doc["metadata"], **chunk["metadata"]},
                            "embedding": vector,
                        },
                    }
                )
                chunk_count += 1
        if actions:
            self._bulk(self._client, actions, refresh=True)
        return {"documents": len(normalized), "chunks": chunk_count}

    def _base_filters(self, args: SearchArgs) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []
        if args.document_id:
            filters.append({"term": {"document_id": args.document_id}})
        if args.source_type:
            filters.append({"term": {"source_type": args.source_type}})
        if args.source_types:
            filters.append({"terms": {"source_type": list(args.source_types)}})
        for key, value in (args.filters or {}).items():
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                filters.append({"terms": {f"metadata.{key}": list(value)}})
            else:
                filters.append({"term": {f"metadata.{key}": value}})
        return filters

    def _doc_chunk_count(self, document_id: str) -> int:
        resp = self._client.count(index=CFG.elastic_chunks_alias, query={"term": {"document_id": document_id}})
        return int(resp.get("count", 0))

    def _search_exact(self, args: SearchArgs, query_vector: list[float]) -> list[dict[str, Any]]:
        filters = self._base_filters(args)
        body = {
            "size": max(1, args.vector_k),
            "query": {
                "script_score": {
                    "query": {"bool": {"filter": filters}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_vector},
                    },
                }
            },
        }
        resp = self._client.search(index=CFG.elastic_chunks_alias, **body)
        return self._extract_hits(resp)

    def _lexical_query(self, args: SearchArgs) -> dict[str, Any]:
        return {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": args.query,
                            "fields": ["text", "title^2", "section_title^1.5"],
                        }
                    }
                ],
                "filter": self._base_filters(args),
            }
        }

    def _search_vector(self, args: SearchArgs, query_vector: list[float]) -> list[dict[str, Any]]:
        filters = self._base_filters(args)
        resp = self._client.search(
            index=CFG.elastic_chunks_alias,
            knn={
                "field": "embedding",
                "query_vector": query_vector,
                "k": max(1, args.vector_k),
                "num_candidates": max(args.vector_k, args.num_candidates),
                "filter": filters or None,
            },
            size=max(1, args.vector_k),
        )
        return self._extract_hits(resp)

    def _search_lexical(self, args: SearchArgs) -> list[dict[str, Any]]:
        resp = self._client.search(index=CFG.elastic_chunks_alias, query=self._lexical_query(args), size=max(1, args.lexical_k))
        return self._extract_hits(resp)

    def _search_rrf_native(self, args: SearchArgs, query_vector: list[float]) -> list[dict[str, Any]]:
        filters = self._base_filters(args)
        body = {
            "size": max(1, args.final_k),
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {
                            "standard": {
                                "query": self._lexical_query(args),
                            }
                        },
                        {
                            "knn": {
                                "field": "embedding",
                                "query_vector": query_vector,
                                "k": max(1, args.vector_k),
                                "num_candidates": max(args.vector_k, args.num_candidates),
                                "filter": filters,
                            }
                        },
                    ],
                    "rank_constant": CFG.elastic_rrf_rank_constant,
                    "rank_window_size": max(args.lexical_k, args.vector_k, args.final_k),
                }
            },
        }
        response = self._client.perform_request(
            "POST",
            f"/{CFG.elastic_chunks_alias}/_search",
            body=body,
        )
        payload = response.body if hasattr(response, "body") else response
        if not isinstance(payload, dict):
            raise RuntimeError("elastic native RRF returned a non-dict payload")
        return self._extract_hits(payload)

    def _extract_hits(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        hits = response.get("hits", {}).get("hits", [])
        out: list[dict[str, Any]] = []
        for rank, hit in enumerate(hits, start=1):
            source = dict(hit.get("_source", {}) or {})
            out.append(
                {
                    "chunk_id": str(source.get("chunk_id") or hit.get("_id", "")),
                    "doc_id": str(source.get("document_id", "")),
                    "document_id": str(source.get("document_id", "")),
                    "chunk_index": int(source.get("chunk_index", 0)),
                    "text": str(source.get("text", "")),
                    "source": str(source.get("source", "")),
                    "source_type": str(source.get("source_type", "")),
                    "source_thread_id": str(source.get("source_thread_id", "")),
                    "source_message_id": str(source.get("source_message_id", "")),
                    "uri": str(source.get("source_uri", "")),
                    "title": str(source.get("title", "")),
                    "timestamp_utc": source.get("timestamp_utc"),
                    "section_title": str(source.get("section_title", "")),
                    "spans": {
                        "timestamp_label": source.get("timestamp_label"),
                        "start_ms": source.get("start_ms"),
                        "end_ms": source.get("end_ms"),
                        "page_start": source.get("page_start"),
                        "page_end": source.get("page_end"),
                        "char_start": source.get("char_start"),
                        "char_end": source.get("char_end"),
                    },
                    "rrf_score": float(hit.get("_score", 0.0) or 0.0),
                    "rank": rank,
                }
            )
        return out

    def _fuse_hits(self, lexical_hits: list[dict[str, Any]], vector_hits: list[dict[str, Any]], final_k: int) -> list[dict[str, Any]]:
        fused: dict[str, dict[str, Any]] = {}
        for hits in (lexical_hits, vector_hits):
            for rank, hit in enumerate(hits, start=1):
                score = 1.0 / (CFG.elastic_rrf_rank_constant + rank)
                key = str(hit["chunk_id"])
                if key not in fused:
                    fused[key] = dict(hit)
                    fused[key]["rrf_score"] = 0.0
                fused[key]["rrf_score"] += score
        ranked = sorted(fused.values(), key=lambda item: float(item["rrf_score"]), reverse=True)
        return ranked[: max(1, final_k)]

    def search(self, args: SearchArgs) -> list[dict[str, Any]]:
        query_vector = self._embed.embed_query(self._model_name, [args.query])[0]
        exact_allowed = bool(args.document_id) and self._doc_chunk_count(args.document_id) <= CFG.elastic_single_doc_exact_max_chunks
        force_exact = args.vector_search_mode == "exact"
        force_approximate = args.vector_search_mode == "approximate"
        use_exact = force_exact or (not force_approximate and exact_allowed)
        retriever_mode = "exact" if use_exact else "approximate"
        use_native_rrf = args.vector_search_mode == "auto" and not use_exact and self._native_rrf_enabled
        if use_native_rrf:
            try:
                hits = self._search_rrf_native(args, query_vector)
                retriever_mode = "native_rrf"
            except Exception as exc:  # noqa: BLE001
                log.warning("native RRF search failed; falling back to client-side RRF: %s", exc)
                lexical_hits = self._search_lexical(args)
                vector_hits = self._search_vector(args, query_vector)
                hits = self._fuse_hits(lexical_hits, vector_hits, args.final_k)
                retriever_mode = "approximate"
        else:
            vector_hits = self._search_exact(args, query_vector) if use_exact else self._search_vector(args, query_vector)
            lexical_hits = self._search_lexical(args)
            hits = self._fuse_hits(lexical_hits, vector_hits, args.final_k)
        for hit in hits:
            hit["model_space"] = args.model_space
            hit["embedding_model"] = self._model_name
            hit["retrieval_profile"] = args.profile
            hit["citations_rendered"] = args.render_citations
            hit["vector_search_mode"] = retriever_mode
        return hits

    def delete(self, source: str | None = None, document_id: str | None = None) -> int:
        filters: list[dict[str, Any]] = []
        if document_id:
            filters.append({"term": {"document_id": document_id}})
        elif source:
            filters.append({"term": {"source": source}})
        else:
            raise ValueError("delete requires source or document_id")
        query = {"bool": {"filter": filters}}
        count = int(self._client.count(index=CFG.elastic_chunks_alias, query=query).get("count", 0))
        self._client.delete_by_query(index=CFG.elastic_chunks_alias, query=query, refresh=True)
        self._client.delete_by_query(index=CFG.elastic_documents_index, query=query, refresh=True)
        return count

    def upsert_response_mapping(
        self,
        *,
        response_id: str,
        document_id: str,
        source_type: str,
        summary_mode: str,
    ) -> dict[str, Any]:
        payload = {
            "response_id": response_id,
            "document_id": document_id,
            "source_type": source_type,
            "summary_mode": summary_mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._client.index(index=CFG.elastic_response_map_index, id=response_id, document=payload, refresh=True)
        return payload

    def resolve_response_mapping(self, response_id: str) -> dict[str, Any] | None:
        try:
            resp = self._client.get(index=CFG.elastic_response_map_index, id=response_id)
        except Exception:
            return None
        source = resp.get("_source")
        return dict(source) if isinstance(source, dict) else None
