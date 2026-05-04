from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import app.embed as embed_mod


class _FakeSentenceTransformer:
    init_calls: list[tuple[str, bool]] = []

    def __init__(self, repo: str, trust_remote_code: bool = False) -> None:
        type(self).init_calls.append((repo, trust_remote_code))
        self.encode_calls: list[list[str]] = []

    def encode(self, texts, normalize_embeddings: bool = True):
        batch = list(texts)
        self.encode_calls.append(batch)
        if len(batch) == 1:
            return [0.1, 0.2, 0.3]
        return [[0.1, 0.2, 0.3] for _ in batch]


class EmbeddingRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeSentenceTransformer.init_calls = []
        self.env_patcher = patch.dict(
            os.environ,
            {
                "MEMORY_EMBED_BATCH_SIZE": "4",
                "MEMORY_EMBED_QUERY_BATCH_SIZE": "3",
                "MEMORY_EMBED_DOCUMENT_BATCH_SIZE": "1",
            },
            clear=False,
        )
        self.env_patcher.start()
        self.model_patcher = patch.object(embed_mod, "SentenceTransformer", _FakeSentenceTransformer)
        self.model_patcher.start()

    def tearDown(self) -> None:
        self.model_patcher.stop()
        self.env_patcher.stop()

    def test_embed_document_batches_serially(self) -> None:
        registry = embed_mod.EmbeddingRegistry()
        vectors = registry.embed_document(
            "studio-nomic-embed-text-v1.5",
            ["one", "two", "three"],
        )
        self.assertEqual(len(vectors), 3)
        model = registry._loaded["studio-nomic-embed-text-v1.5"]
        self.assertEqual(
            model.encode_calls,
            [
                ["search_document: one"],
                ["search_document: two"],
                ["search_document: three"],
            ],
        )

    def test_embed_query_uses_configured_batch_size(self) -> None:
        registry = embed_mod.EmbeddingRegistry()
        vectors = registry.embed_query(
            "studio-nomic-embed-text-v1.5",
            ["one", "two", "three", "four"],
        )
        self.assertEqual(len(vectors), 4)
        model = registry._loaded["studio-nomic-embed-text-v1.5"]
        self.assertEqual(
            model.encode_calls,
            [
                ["search_query: one", "search_query: two", "search_query: three"],
                ["search_query: four"],
            ],
        )

    def test_model_load_is_cached(self) -> None:
        registry = embed_mod.EmbeddingRegistry()
        registry.embed_document("studio-nomic-embed-text-v1.5", ["one"])
        registry.embed_document("studio-nomic-embed-text-v1.5", ["two"])
        self.assertEqual(len(_FakeSentenceTransformer.init_calls), 1)


if __name__ == "__main__":
    unittest.main()
