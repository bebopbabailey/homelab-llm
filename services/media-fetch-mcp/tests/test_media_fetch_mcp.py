import unittest
from unittest import mock

import media_fetch_mcp as mod


class DummyFetchedTranscript:
    def __init__(self, rows):
        self._rows = rows

    def to_raw_data(self):
        return list(self._rows)


class DummyTranscript:
    def __init__(self, language, is_generated, rows, *, language_code=""):
        self.language = language
        self.language_code = language_code
        self.is_generated = is_generated
        self._rows = rows

    def fetch(self):
        return DummyFetchedTranscript(self._rows)


class DummyTranscriptList:
    def __init__(self, entries):
        self._entries = list(entries)

    def __iter__(self):
        return iter(self._entries)


class DummyTranscriptApi:
    def __init__(self, transcript_list):
        self._transcript_list = transcript_list

    def list(self, video_id):
        self.video_id = video_id
        return self._transcript_list


class MediaFetchMcpTests(unittest.TestCase):
    def test_extract_video_id_accepts_common_single_video_forms(self):
        self.assertEqual(mod._extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(mod._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(mod._extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(mod._extract_video_id("https://www.youtube.com/live/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_extract_video_id_rejects_invalid_or_unsupported_urls(self):
        with self.assertRaisesRegex(mod.ToolContractError, r"^invalid_url:"):
            mod._extract_video_id("notaurl")
        with self.assertRaisesRegex(mod.ToolContractError, r"^unsupported_url:"):
            mod._extract_video_id("https://www.youtube.com/playlist?list=PL123")
        with self.assertRaisesRegex(mod.ToolContractError, r"^unsupported_url:"):
            mod._extract_video_id("https://www.youtube.com/@example")

    def test_fetch_prefers_manual_track_over_generated(self):
        transcript_list = DummyTranscriptList(
            [
                DummyTranscript("English", True, [{"text": "generated", "start": 0.0}], language_code="en"),
                DummyTranscript("English", False, [{"text": "manual", "start": 0.0}], language_code="en"),
            ]
        )
        with mock.patch.object(mod, "YouTubeTranscriptApi", return_value=DummyTranscriptApi(transcript_list)):
            payload = mod._fetch_transcript_payload("https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(payload["caption_type"], "manual")
        self.assertEqual(payload["source_url"], "https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(payload["language_code"], "en")
        self.assertEqual(payload["segments"][0]["timestamp_label"], "00:00")
        self.assertIn("[00:00] manual", payload["transcript_text"])

    def test_fetch_builds_structured_segments_and_skips_empty_noise(self):
        transcript_list = DummyTranscriptList(
            [
                DummyTranscript(
                    "German",
                    False,
                    [
                        {"text": " Hallo    Welt ", "start": 0.0},
                        {"text": "   ", "start": 1.0},
                        {"text": " -- ", "start": 2.0},
                        {"text": "Noch ein Satz", "start": 65.0, "duration": 2.0},
                    ],
                    language_code="de",
                )
            ]
        )
        with mock.patch.object(mod, "YouTubeTranscriptApi", return_value=DummyTranscriptApi(transcript_list)):
            payload = mod.youtube_transcript("https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(payload["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(payload["source_url"], "https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(payload["language"], "German")
        self.assertEqual(payload["language_code"], "de")
        self.assertEqual(payload["caption_type"], "manual")
        self.assertEqual(payload["transcript_text"], "[00:00] Hallo Welt\n[01:05] Noch ein Satz")
        self.assertEqual(
            payload["segments"],
            [
                {"text": "Hallo Welt", "start": 0.0, "duration": 0.0, "timestamp_label": "00:00"},
                {"text": "Noch ein Satz", "start": 65.0, "duration": 2.0, "timestamp_label": "01:05"},
            ],
        )

    def test_fetch_maps_missing_transcript_to_no_transcript(self):
        class NoTranscriptApi:
            def list(self, video_id):
                raise RuntimeError("No transcripts were found")

        with mock.patch.object(mod, "YouTubeTranscriptApi", return_value=NoTranscriptApi()):
            with self.assertRaisesRegex(mod.ToolContractError, r"^no_transcript:"):
                mod.youtube_transcript("https://youtu.be/dQw4w9WgXcQ")

    def test_fetch_maps_other_errors_to_upstream_failure(self):
        class BrokenApi:
            def list(self, video_id):
                raise RuntimeError("boom")

        with mock.patch.object(mod, "YouTubeTranscriptApi", return_value=BrokenApi()):
            with self.assertRaisesRegex(mod.ToolContractError, r"^upstream_failure:"):
                mod.youtube_transcript("https://youtu.be/dQw4w9WgXcQ")

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
