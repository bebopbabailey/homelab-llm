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


if __name__ == "__main__":
    unittest.main()
