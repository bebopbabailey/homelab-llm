from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.openwebui_knowledge_sync import (
    KnowledgeRuntimeConfig,
    build_embedding_payload,
    build_rag_payload,
    desired_runtime_config,
    embedding_config_matches,
    rag_config_matches,
)


class KnowledgeSyncTests(unittest.TestCase):
    def test_desired_runtime_config_uses_backend_defaults(self) -> None:
        cfg = desired_runtime_config({})
        self.assertEqual(cfg.embedding_engine, "openai")
        self.assertEqual(cfg.embedding_model, "studio-nomic-embed-text-v1.5")
        self.assertEqual(cfg.top_k, 5)
        self.assertTrue(cfg.enable_hybrid_search)
        self.assertEqual(cfg.chunk_size, 1000)
        self.assertEqual(cfg.chunk_overlap, 100)

    def test_embedding_payload_and_match(self) -> None:
        cfg = KnowledgeRuntimeConfig(
            embedding_engine="openai",
            embedding_model="studio-nomic-embed-text-v1.5",
            embedding_batch_size=1,
            embedding_concurrent_requests=0,
            enable_async_embedding=True,
            openai_base_url="http://192.168.1.72:55440/v1",
            openai_api_key="dummy",
            top_k=5,
            rag_full_context=False,
            enable_hybrid_search=True,
            enable_hybrid_search_enriched_texts=True,
            relevance_threshold=0.0,
            chunk_size=1000,
            chunk_overlap=100,
        )
        payload = build_embedding_payload(cfg)
        self.assertTrue(
            embedding_config_matches(
                {
                    "RAG_EMBEDDING_ENGINE": "openai",
                    "RAG_EMBEDDING_MODEL": "studio-nomic-embed-text-v1.5",
                    "RAG_EMBEDDING_BATCH_SIZE": 1,
                    "ENABLE_ASYNC_EMBEDDING": True,
                    "RAG_EMBEDDING_CONCURRENT_REQUESTS": 0,
                    "openai_config": {"url": "http://192.168.1.72:55440/v1", "key": "dummy"},
                },
                payload,
            )
        )

    def test_rag_payload_and_match(self) -> None:
        cfg = KnowledgeRuntimeConfig(
            embedding_engine="openai",
            embedding_model="studio-nomic-embed-text-v1.5",
            embedding_batch_size=1,
            embedding_concurrent_requests=0,
            enable_async_embedding=True,
            openai_base_url="http://192.168.1.72:55440/v1",
            openai_api_key="dummy",
            top_k=5,
            rag_full_context=False,
            enable_hybrid_search=True,
            enable_hybrid_search_enriched_texts=True,
            relevance_threshold=0.0,
            chunk_size=1000,
            chunk_overlap=100,
        )
        payload = build_rag_payload(cfg)
        self.assertTrue(
            rag_config_matches(
                {
                    "TOP_K": 5,
                    "RAG_FULL_CONTEXT": False,
                    "ENABLE_RAG_HYBRID_SEARCH": True,
                    "ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS": True,
                    "RELEVANCE_THRESHOLD": 0.0,
                    "CHUNK_SIZE": 1000,
                    "CHUNK_OVERLAP": 100,
                },
                payload,
            )
        )


if __name__ == "__main__":
    unittest.main()
