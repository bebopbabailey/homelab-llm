from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from app.backends.base import SearchArgs
from app.backends.elastic import ElasticBackend


class _FakeResponse:
    def __init__(self, body):
        self.body = body


class _FakeIndicesClient:
    def __init__(self) -> None:
        self.created: dict[str, dict] = {}
        self.aliases: dict[str, str] = {}

    def exists(self, index: str) -> bool:
        return index in self.created

    def create(self, index: str, mappings: dict) -> None:
        self.created[index] = mappings

    def exists_alias(self, name: str) -> bool:
        return name in self.aliases

    def put_alias(self, index: str, name: str) -> None:
        self.aliases[name] = index


class _FakeElasticsearch:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.indices = _FakeIndicesClient()
        self.docs: dict[str, dict] = {}
        self.response_maps: dict[str, dict] = {}
        self.document_chunk_counts: dict[str, int] = {"doc-small": 2, "doc-large": 2000}
        self.search_calls: list[dict] = []
        self.perform_calls: list[dict] = []

    def info(self) -> dict:
        return {"cluster_name": "memory-cluster", "version": {"number": "9.2.0"}}

    def perform_request(self, method: str, path: str, body=None):
        if path == "/_license":
            return _FakeResponse({"license": {"type": "basic", "status": "active"}})
        self.perform_calls.append({"method": method, "path": path, "body": body})
        return _FakeResponse(
            {
                "hits": {
                    "hits": [
                        {
                            "_id": "chunk-native",
                            "_score": 7.0,
                            "_source": {
                                "document_id": "doc-large",
                                "chunk_id": "chunk-native",
                                "chunk_index": 0,
                                "text": "native rrf text",
                                "source": "youtube",
                                "source_type": "youtube",
                                "title": "native title",
                                "source_uri": "https://example.test/native",
                                "timestamp_label": "00:00",
                                "start_ms": 0,
                                "end_ms": 1000,
                            },
                        }
                    ]
                }
            }
        )

    def count(self, index: str, query=None) -> dict:
        if query and query.get("term", {}).get("document_id"):
            doc_id = query["term"]["document_id"]
            return {"count": self.document_chunk_counts.get(doc_id, 0)}
        if index.endswith("documents-v1"):
            return {"count": len(self.docs)}
        if index.endswith("response-map-v1"):
            return {"count": len(self.response_maps)}
        return {"count": 3}

    def search(self, index: str, **kwargs) -> dict:
        self.search_calls.append({"index": index, **kwargs})
        if "knn" in kwargs:
            chunk_id = "chunk-vector"
            document_id = "doc-large"
            score = 6.0
        else:
            chunk_id = "chunk-lexical"
            document_id = "doc-small"
            score = 5.0
        return {
            "hits": {
                "hits": [
                    {
                        "_id": chunk_id,
                        "_score": score,
                        "_source": {
                            "document_id": document_id,
                            "chunk_id": chunk_id,
                            "chunk_index": 0,
                            "text": f"text for {chunk_id}",
                            "source": "youtube",
                            "source_type": "youtube",
                            "title": f"title for {chunk_id}",
                            "source_uri": "https://example.test/doc",
                            "timestamp_label": "00:00",
                            "start_ms": 0,
                            "end_ms": 1000,
                        },
                    }
                ]
            }
        }

    def index(self, index: str, id: str, document: dict, refresh: bool = False) -> None:
        if index.endswith("response-map-v1"):
            self.response_maps[id] = document
        else:
            self.docs[id] = document

    def get(self, index: str, id: str) -> dict:
        if index.endswith("response-map-v1") and id in self.response_maps:
            return {"_source": self.response_maps[id]}
        raise KeyError(id)

    def delete_by_query(self, index: str, query: dict, refresh: bool = False) -> None:
        return None


class _FakeEmbedRegistry:
    def model_info(self, model_name: str) -> dict:
        return {
            "model_id": model_name,
            "hf_repo": "fake/repo",
            "default_dimension": 3,
            "query_prefix": "search_query:",
            "document_prefix": "search_document:",
            "prefix_mode": "search_query/search_document",
        }

    def embed(self, model_name: str, texts) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in list(texts)]

    def embed_query(self, model_name: str, texts) -> list[list[float]]:
        return self.embed(model_name, texts)

    def embed_document(self, model_name: str, texts) -> list[list[float]]:
        return self.embed(model_name, texts)


class ElasticBackendTests(unittest.TestCase):
    def _build_backend(self) -> tuple[ElasticBackend, _FakeElasticsearch]:
        fake_es_module = types.SimpleNamespace(Elasticsearch=_FakeElasticsearch)
        fake_helpers_module = types.SimpleNamespace(bulk=lambda client, actions, refresh=True: (len(actions), []))
        with patch.dict(
            "sys.modules",
            {
                "elasticsearch": fake_es_module,
                "elasticsearch.helpers": fake_helpers_module,
            },
        ):
            with patch("app.backends.elastic.EmbeddingRegistry", return_value=_FakeEmbedRegistry()):
                backend = ElasticBackend()
        return backend, backend._client  # type: ignore[attr-defined]

    def test_explicit_dense_vector_mapping_and_stats(self) -> None:
        backend, client = self._build_backend()
        chunk_mapping = client.indices.created[backend._physical_chunks_index]["properties"]["embedding"]
        self.assertEqual(chunk_mapping["type"], "dense_vector")
        self.assertEqual(chunk_mapping["dims"], 3)
        self.assertEqual(chunk_mapping["similarity"], "cosine")
        self.assertTrue(chunk_mapping["index"])
        self.assertEqual(chunk_mapping["index_options"]["type"], "int8_hnsw")
        self.assertEqual(chunk_mapping["index_options"]["m"], 16)
        self.assertEqual(chunk_mapping["index_options"]["ef_construction"], 100)

        stats = backend.stats()
        self.assertEqual(stats["vector_index_type"], "int8_hnsw")
        self.assertEqual(stats["embedding_dims"], 3)
        self.assertEqual(stats["embedding_prefix_mode"], "search_query/search_document")
        self.assertTrue(stats["native_rrf_capable"])

    def test_search_uses_exact_for_small_single_document(self) -> None:
        backend, client = self._build_backend()
        hits = backend.search(
            SearchArgs(
                query="workflow",
                top_k=8,
                lexical_k=24,
                vector_k=24,
                num_candidates=96,
                final_k=8,
                model_space="qwen",
                profile="precise",
                document_id="doc-small",
            )
        )
        self.assertEqual(hits[0]["vector_search_mode"], "exact")
        self.assertFalse(client.perform_calls)

    def test_search_uses_native_rrf_for_large_document_scope(self) -> None:
        backend, client = self._build_backend()
        hits = backend.search(
            SearchArgs(
                query="workflow",
                top_k=10,
                lexical_k=48,
                vector_k=48,
                num_candidates=192,
                final_k=10,
                model_space="qwen",
                profile="balanced",
                document_id="doc-large",
                source_type="youtube",
            )
        )
        self.assertEqual(hits[0]["vector_search_mode"], "native_rrf")
        self.assertTrue(client.perform_calls)
        body = client.perform_calls[0]["body"]
        self.assertIn("retriever", body)
        self.assertEqual(body["retriever"]["rrf"]["rank_constant"], 60)

    def test_response_mapping_round_trip(self) -> None:
        backend, _client = self._build_backend()
        payload = backend.upsert_response_mapping(
            response_id="resp_123",
            document_id="youtube:abc123",
            source_type="youtube",
            summary_mode="indexed_long",
        )
        self.assertEqual(payload["document_id"], "youtube:abc123")
        resolved = backend.resolve_response_mapping("resp_123")
        self.assertEqual(resolved["summary_mode"], "indexed_long")


if __name__ == "__main__":
    unittest.main()
