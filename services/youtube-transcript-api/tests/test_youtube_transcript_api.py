from __future__ import annotations

from unittest import mock

from fastapi.testclient import TestClient

from youtube_transcript_api_service import transcripts
from youtube_transcript_api_service.app import app


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
        return self._transcript_list


def test_extract_video_id_accepts_common_single_video_forms():
    assert transcripts.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert transcripts.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert transcripts.extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert transcripts.extract_video_id("https://www.youtube.com/live/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_rejects_invalid_or_unsupported_urls():
    for url in ("notaurl", "https://www.youtube.com/playlist?list=PL123", "https://www.youtube.com/@example"):
        try:
            transcripts.extract_video_id(url)
        except transcripts.TranscriptError as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError(f"expected TranscriptError for {url}")


def test_fetch_prefers_manual_track_and_builds_canonical_document():
    transcript_list = DummyTranscriptList(
        [
            DummyTranscript("English", True, [{"text": "generated", "start": 0.0}], language_code="en"),
            DummyTranscript("English", False, [{"text": " manual   words ", "start": 5.0, "duration": 2.0}], language_code="en"),
        ]
    )
    with mock.patch.object(transcripts, "YouTubeTranscriptApi", return_value=DummyTranscriptApi(transcript_list)):
        document = transcripts.fetch_transcript("https://youtu.be/dQw4w9WgXcQ")
    assert document.source_type == "youtube"
    assert document.source_id == "dQw4w9WgXcQ"
    assert document.canonical_url == "https://youtu.be/dQw4w9WgXcQ"
    assert document.caption_type == "manual"
    assert document.language_code == "en"
    assert document.transcript_text == "[00:05] manual words"
    assert len(document.content_hash) == 64
    assert document.segments == [{"text": "manual words", "start": 5.0, "duration": 2.0, "timestamp_label": "00:05"}]


def test_fetch_uses_generated_track_when_manual_is_unavailable():
    transcript_list = DummyTranscriptList(
        [DummyTranscript("English", True, [{"text": "generated words", "start": 0.0}], language_code="en")]
    )
    with mock.patch.object(transcripts, "YouTubeTranscriptApi", return_value=DummyTranscriptApi(transcript_list)):
        document = transcripts.fetch_transcript("https://youtu.be/dQw4w9WgXcQ")
    assert document.caption_type == "generated"
    assert document.transcript_text == "[00:00] generated words"


def test_fetch_maps_missing_transcript_to_404_error():
    class NoTranscriptApi:
        def list(self, video_id):
            raise RuntimeError("No transcripts were found")

    with mock.patch.object(transcripts, "YouTubeTranscriptApi", return_value=NoTranscriptApi()):
        try:
            transcripts.fetch_transcript("https://youtu.be/dQw4w9WgXcQ")
        except transcripts.TranscriptError as exc:
            assert exc.code == "no_transcript"
            assert exc.status_code == 404
        else:
            raise AssertionError("expected TranscriptError")


def test_chat_completion_returns_plain_transcript_content():
    document = transcripts.TranscriptDocument(
        source_type="youtube",
        source_id="dQw4w9WgXcQ",
        canonical_url="https://youtu.be/dQw4w9WgXcQ",
        language="English",
        language_code="en",
        caption_type="manual",
        transcript_text="[00:00] hello",
        content_hash="a" * 64,
        segments=[{"text": "hello", "start": 0.0, "duration": 1.0, "timestamp_label": "00:00"}],
    )
    with mock.patch("youtube_transcript_api_service.app.fetch_transcript", return_value=document):
        response = TestClient(app).post(
            "/v1/chat/completions",
            json={
                "model": "youtube-transcript",
                "messages": [{"role": "user", "content": "https://youtu.be/dQw4w9WgXcQ"}],
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "[00:00] hello"
    assert body["transcript"]["segments"][0]["text"] == "hello"
