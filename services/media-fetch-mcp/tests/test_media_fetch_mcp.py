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
