import unittest
from unittest import mock

import media_fetch_mcp as mod


class MediaFetchMcpTests(unittest.TestCase):
    def test_youtube_tool_is_not_owned_by_media_fetch_mcp(self):
        self.assertFalse(hasattr(mod, "youtube_transcript"))

    def test_search_normalizes_direct_searxng_results(self):
        with mock.patch.object(
            mod,
            "_http_json",
            return_value={
                "results": [
                    {"title": "One", "url": "https://example.com/one", "content": "alpha", "engine": "bing"},
                    {"title": "Two", "url": "https://example.com/two", "content": "beta"},
                ]
            },
        ) as http_json:
            payload = mod.media_fetch_web_search("hello world", max_results=2)
        self.assertEqual(payload["query"], "hello world")
        self.assertEqual(payload["provider"], "searxng")
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0]["snippet"], "alpha")
        self.assertEqual(payload["results"][0]["engine"], "bing")
        http_json.assert_called_once()

    def test_session_upsert_maps_conversation_to_research_document(self):
        cleaned = {
            "requested_url": "https://example.com/post",
            "final_url": "https://example.com/post",
            "canonical_url": "https://example.com/post",
            "title": "Example Post",
            "site_name": "Example",
            "description": "desc",
            "markdown": "# Heading\n\nFirst block.\n\nSecond block.",
            "clean_text": "Heading First block. Second block.",
            "quality_label": "high",
            "quality_flags": [],
            "content_stats": {"chars": 10},
            "extractor_used": "trafilatura",
            "content_sha256": "abc123",
        }
        with mock.patch.object(mod, "_http_json", return_value={"ok": True, "documents": 1, "chunks": 2}) as http_json, \
             mock.patch.object(mod, "_vector_db_write_bearer_token", return_value="secret-token"):
            payload = mod.media_fetch_web_session_upsert("chat-123", [cleaned])
        self.assertEqual(payload["document_id"], "research:chat-123")
        self.assertEqual(payload["conversation_id"], "chat-123")
        called_json = http_json.call_args.kwargs["json_payload"]
        upsert_doc = called_json["documents"][0]
        self.assertEqual(upsert_doc["document_id"], "research:chat-123")
        self.assertEqual(upsert_doc["source_thread_id"], "chat-123")
        self.assertEqual(upsert_doc["source_type"], mod.WEB_SOURCE_TYPE)
        self.assertEqual(upsert_doc["uri"], "https://example.com/post")
        self.assertGreaterEqual(len(upsert_doc["chunks"]), 1)
        self.assertEqual(upsert_doc["chunks"][0]["metadata"]["canonical_url"], "https://example.com/post")

    def test_session_search_normalizes_chunk_level_hits(self):
        with mock.patch.object(
            mod,
            "_http_json",
            return_value={
                "query": "who said what",
                "profile": "balanced",
                "hits": [
                    {
                        "document_id": "research:chat-123",
                        "chunk_id": "chunk-1",
                        "title": "Doc",
                        "text": "useful chunk",
                        "section_title": "Findings",
                        "metadata": {"canonical_url": "https://example.com/post", "site_name": "Example"},
                    }
                ],
            },
        ):
            payload = mod.media_fetch_web_session_search("chat-123", "who said what")
        self.assertEqual(payload["document_id"], "research:chat-123")
        self.assertEqual(payload["hits"][0]["source_url"], "https://example.com/post")
        self.assertEqual(payload["hits"][0]["site_name"], "Example")
        self.assertEqual(payload["hits"][0]["text"], "useful chunk")

    def test_session_delete_targets_research_document(self):
        with mock.patch.object(mod, "_http_json", return_value={"ok": True, "deleted_documents": 1}) as http_json, \
             mock.patch.object(mod, "_vector_db_write_bearer_token", return_value="secret-token"):
            payload = mod.media_fetch_web_session_delete("chat-123")
        self.assertEqual(payload["document_id"], "research:chat-123")
        self.assertEqual(http_json.call_args.kwargs["json_payload"], {"document_id": "research:chat-123"})

    def test_quick_helper_runs_search_fetch_upsert_and_retrieve(self):
        with mock.patch.object(
            mod,
            "_search_web_raw",
            return_value={
                "query": "test query",
                "results": [
                    {"url": "https://example.com/one", "title": "One"},
                    {"url": "https://example.com/two", "title": "Two"},
                ],
            },
        ), mock.patch.object(
            mod,
            "_web_fetch_raw",
            side_effect=[
                {"canonical_url": "https://example.com/one", "title": "One", "quality_label": "high", "extractor_used": "trafilatura"},
                {"canonical_url": "https://example.com/two", "title": "Two", "quality_label": "medium", "extractor_used": "readability"},
            ],
        ) as fetch_raw, mock.patch.object(
            mod,
            "_vector_db_upsert",
            return_value={"documents": 2, "chunks": 5},
        ) as upsert, mock.patch.object(
            mod,
            "_vector_db_search",
            return_value={"hits": [{"chunk_id": "c1", "text": "answer"}]},
        ) as search:
            payload = mod.media_fetch_web_quick("chat-123", "test query")
        self.assertEqual(payload["document_id"], "research:chat-123")
        self.assertEqual(payload["stored"]["documents"], 2)
        self.assertEqual(len(payload["sources"]), 2)
        self.assertEqual(payload["evidence"][0]["chunk_id"], "c1")
        self.assertEqual(fetch_raw.call_count, 2)
        upsert.assert_called_once()
        search.assert_called_once()

    def test_research_helper_returns_broader_search_metadata(self):
        with mock.patch.object(
            mod,
            "_search_web_raw",
            return_value={"query": "test query", "results": [{"url": "https://example.com/one", "title": "One"}]},
        ), mock.patch.object(
            mod,
            "_web_fetch_raw",
            return_value={"canonical_url": "https://example.com/one", "title": "One", "quality_label": "high", "extractor_used": "trafilatura"},
        ), mock.patch.object(
            mod,
            "_vector_db_upsert",
            return_value={"documents": 1, "chunks": 3},
        ), mock.patch.object(
            mod,
            "_vector_db_search",
            return_value={"hits": [{"chunk_id": "c1", "text": "evidence"}], "profile": "broad"},
        ):
            payload = mod.media_fetch_web_research("chat-123", "test query")
        self.assertEqual(payload["document_id"], "research:chat-123")
        self.assertIn("search", payload)
        self.assertIn("retrieval", payload)
        self.assertEqual(payload["stored"]["chunks"], 3)


if __name__ == "__main__":
    unittest.main()
