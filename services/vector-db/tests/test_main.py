from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import _BACKEND, app
import app.main as main_mod


class _DummyBackend:
    def __init__(self) -> None:
        self.last_search_args = None

    def health(self):
        return {"ok": True, "backend": "dummy"}

    def stats(self):
        return {"backend": "dummy"}

    def upsert(self, documents):
        return {"documents": len(documents), "chunks": len(documents)}

    def search(self, args):
        self.last_search_args = args
        return [{"chunk_id": "1", "text": "alpha"}]

    def delete(self, source=None, document_id=None):
        return 1

    def upsert_response_mapping(self, *, response_id, document_id, source_type, summary_mode):
        return {
            "response_id": response_id,
            "document_id": document_id,
            "source_type": source_type,
            "summary_mode": summary_mode,
        }

    def resolve_response_mapping(self, response_id):
        if response_id == "missing":
            return None
        return {
            "response_id": response_id,
            "document_id": "youtube:abc123",
            "source_type": "youtube",
            "summary_mode": "indexed_long",
        }


class MainApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = _DummyBackend()
        main_mod._BACKEND = self.backend
        self.client = TestClient(app)

    def tearDown(self) -> None:
        main_mod._BACKEND = None

    def test_search_applies_profile_defaults_and_filters(self) -> None:
        response = self.client.post(
            "/v1/memory/search",
            json={
                "query": "main claims",
                "profile": "balanced",
                "document_id": "youtube:abc123",
                "source_type": "youtube",
                "vector_search_mode": "exact",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"], "balanced")
        self.assertEqual(self.backend.last_search_args.document_id, "youtube:abc123")
        self.assertEqual(self.backend.last_search_args.source_type, "youtube")
        self.assertEqual(self.backend.last_search_args.final_k, 10)
        self.assertEqual(self.backend.last_search_args.vector_search_mode, "exact")

    def test_response_map_resolve_404s_when_missing(self) -> None:
        response = self.client.post("/v1/memory/response-map/resolve", json={"response_id": "missing"})
        self.assertEqual(response.status_code, 404)

    def test_write_routes_require_bearer_when_configured(self) -> None:
        with unittest.mock.patch("app.main.memory_api_write_bearer_token", return_value="secret-token"):
            response = self.client.post(
                "/v1/memory/upsert",
                json={"documents": [{"source": "youtube", "text": "hello"}]},
            )
            self.assertEqual(response.status_code, 401)

            response = self.client.post(
                "/v1/memory/upsert",
                headers={"Authorization": "Bearer wrong-token"},
                json={"documents": [{"source": "youtube", "text": "hello"}]},
            )
            self.assertEqual(response.status_code, 403)

            response = self.client.post(
                "/v1/memory/upsert",
                headers={"Authorization": "Bearer secret-token"},
                json={"documents": [{"source": "youtube", "text": "hello"}]},
            )
            self.assertEqual(response.status_code, 200)

    def test_embeddings_uses_query_prefix_mode(self) -> None:
        with (
            unittest.mock.patch.object(main_mod._embed, "model_config") as model_config,
            unittest.mock.patch.object(main_mod._embed, "embed_query") as embed_query,
            unittest.mock.patch.object(main_mod._embed, "embed_document") as embed_document,
            unittest.mock.patch.object(main_mod._embed, "embed") as embed_raw,
        ):
            model_config.return_value = unittest.mock.Mock(
                query_prefix="search_query:",
                document_prefix="search_document:",
            )
            embed_query.return_value = [[0.1, 0.2]]
            response = self.client.post(
                "/v1/embeddings",
                json={
                    "model": "studio-nomic-embed-text-v1.5",
                    "input": ["how do i send midi clock"],
                    "prefix": "search_query:",
                },
            )
        self.assertEqual(response.status_code, 200)
        embed_query.assert_called_once_with(
            "studio-nomic-embed-text-v1.5",
            ["how do i send midi clock"],
        )
        embed_document.assert_not_called()
        embed_raw.assert_not_called()

    def test_embeddings_accept_string_input_and_unknown_prefix(self) -> None:
        with (
            unittest.mock.patch.object(main_mod._embed, "model_config") as model_config,
            unittest.mock.patch.object(main_mod._embed, "embed") as embed_raw,
        ):
            model_config.return_value = unittest.mock.Mock(
                query_prefix="search_query:",
                document_prefix="search_document:",
            )
            embed_raw.return_value = [[0.9, 0.3]]
            response = self.client.post(
                "/v1/embeddings",
                json={
                    "model": "studio-nomic-embed-text-v1.5",
                    "input": "patch bay routing",
                    "prefix": "manual:",
                },
            )
        self.assertEqual(response.status_code, 200)
        embed_raw.assert_called_once_with(
            "studio-nomic-embed-text-v1.5",
            ["manual: patch bay routing"],
        )


if __name__ == "__main__":
    unittest.main()
