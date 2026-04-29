import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


prompt_guardrail = _load_module(
    REPO_ROOT / "services/litellm-orch/config/prompt_guardrail.py",
    "prompt_guardrail",
)
sys.modules["config.prompt_guardrail"] = prompt_guardrail
youtube_summary_guardrail = _load_module(
    REPO_ROOT / "services/litellm-orch/config/youtube_summary_guardrail.py",
    "youtube_summary_guardrail",
)


class DummyFetchedTranscript:
    def __init__(self, rows):
        self._rows = rows

    def to_raw_data(self):
        return list(self._rows)


class DummyTranscript:
    def __init__(self, language, language_code, is_generated, rows, *, is_translatable=False, translated_rows=None):
        self.video_id = "dQw4w9WgXcQ"
        self.language = language
        self.language_code = language_code
        self.is_generated = is_generated
        self.is_translatable = is_translatable
        self.translation_languages = [{"language_code": "en"}] if is_translatable else []
        self._rows = rows
        self._translated_rows = translated_rows or rows

    def fetch(self):
        return DummyFetchedTranscript(self._rows)

    def translate(self, language_code):
        if language_code != "en" or not self.is_translatable:
            raise RuntimeError("translation unavailable")
        return DummyTranscript(
            "English",
            "en",
            self.is_generated,
            self._translated_rows,
            is_translatable=False,
        )


class DummyTranscriptList:
    def __init__(self, *, manual_en=None, generated_en=None, manual_other=None, generated_other=None):
        self.manual_en = manual_en
        self.generated_en = generated_en
        self.manual_other = manual_other or []
        self.generated_other = generated_other or []

    def find_manually_created_transcript(self, languages):
        if "en" in languages and self.manual_en is not None:
            return self.manual_en
        raise RuntimeError("manual missing")

    def find_generated_transcript(self, languages):
        if "en" in languages and self.generated_en is not None:
            return self.generated_en
        raise RuntimeError("generated missing")

    def __iter__(self):
        return iter([*self.manual_other, *self.generated_other])


class DummyTranscriptApi:
    def __init__(self, transcript_list):
        self._transcript_list = transcript_list

    def list(self, video_id):
        self.video_id = video_id
        return self._transcript_list


class TestYouTubeSummaryHelpers(unittest.TestCase):
    def test_extract_url_and_focus_request(self):
        url, video_id, focus = youtube_summary_guardrail._extract_url_and_focus_request(
            "https://youtu.be/dQw4w9WgXcQ focus on claims and examples"
        )
        self.assertEqual(url, "https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(video_id, "dQw4w9WgXcQ")
        self.assertEqual(focus, "focus on claims and examples")

    def test_split_into_chunks_respects_boundaries(self):
        segments = [
            {"timestamp": "00:00", "text": "alpha " * 400, "start": 0.0, "duration": 10.0},
            {"timestamp": "01:00", "text": "beta " * 400, "start": 60.0, "duration": 10.0},
            {"timestamp": "02:00", "text": "gamma " * 400, "start": 120.0, "duration": 10.0},
        ]
        chunks = youtube_summary_guardrail._split_into_chunks(segments, max_tokens=1300)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["start_timestamp"], "00:00")
        self.assertEqual(chunks[0]["end_timestamp"], "01:00")
        self.assertEqual(chunks[1]["start_timestamp"], "02:00")

    def test_fetch_transcript_falls_back_to_translated_manual(self):
        transcript_list = DummyTranscriptList(
            manual_other=[
                DummyTranscript(
                    "German",
                    "de",
                    False,
                    [{"text": "Hallo Welt", "start": 0.0, "duration": 1.0}],
                    is_translatable=True,
                    translated_rows=[{"text": "Hello world", "start": 0.0, "duration": 1.0}],
                )
            ]
        )
        with patch.object(
            youtube_summary_guardrail,
            "YouTubeTranscriptApi",
            return_value=DummyTranscriptApi(transcript_list),
        ):
            result = youtube_summary_guardrail._fetch_transcript("dQw4w9WgXcQ")
        self.assertEqual(result.caption_type, "translated-manual")
        self.assertEqual(result.transcript_language_code, "en")
        self.assertIn("[00:00] Hello world", result.transcript_text)


class TestYouTubeSummaryGuardrail(unittest.TestCase):
    def test_pre_call_initial_responses_sets_prompt_id_and_prompt_variables(self):
        transcript = youtube_summary_guardrail.TranscriptFetchResult(
            video_id="dQw4w9WgXcQ",
            transcript_text="[00:00] hello world",
            transcript_language="English",
            transcript_language_code="en",
            caption_type="manual",
            was_translated=False,
            token_estimate=1200,
            segments=[{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
        )
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(youtube_summary_guardrail, "_fetch_transcript", return_value=transcript):
            result = asyncio.run(
                guardrail.async_pre_call_hook(
                    None,
                    None,
                    {
                        "model": "task-youtube-summary",
                        "input": [{"role": "user", "content": "https://youtu.be/dQw4w9WgXcQ focus on the conclusion"}],
                    },
                    "responses",
                )
            )
        self.assertEqual(result["prompt_id"], "task-youtube-summary")
        self.assertEqual(result["prompt_variables"]["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(result["prompt_variables"]["focus_request"], "focus on the conclusion")
        self.assertEqual(result["max_output_tokens"], 2048)

        rendered = asyncio.run(
            prompt_guardrail.PromptGuardrail("prompt-pre", "pre_call", True).async_pre_call_hook(
                None,
                None,
                result,
                "responses",
            )
        )
        self.assertEqual(rendered["model"], "task-youtube-summary")
        self.assertIn("Video ID: dQw4w9WgXcQ", rendered["input"][-1]["content"])
        self.assertIn("Transcript:\n[00:00] hello world", rendered["input"][-1]["content"])

    def test_pre_call_followup_passthroughs_without_refetch(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(youtube_summary_guardrail, "_fetch_transcript") as fetch_mock:
            result = asyncio.run(
                guardrail.async_pre_call_hook(
                    None,
                    None,
                    {
                        "model": "task-youtube-summary",
                        "previous_response_id": "resp_123",
                        "input": [{"role": "user", "content": "What were the main claims?"}],
                    },
                    "responses",
                )
            )
        fetch_mock.assert_not_called()
        self.assertEqual(result["previous_response_id"], "resp_123")
        self.assertNotIn("prompt_id", result)

    def test_pre_call_chunked_uses_placeholder(self):
        transcript = youtube_summary_guardrail.TranscriptFetchResult(
            video_id="dQw4w9WgXcQ",
            transcript_text="[00:00] hello world",
            transcript_language="English",
            transcript_language_code="en",
            caption_type="manual",
            was_translated=False,
            token_estimate=youtube_summary_guardrail.SINGLE_PASS_TRANSCRIPT_TOKENS + 1,
            segments=[{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
        )
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(youtube_summary_guardrail, "_fetch_transcript", return_value=transcript):
            result = asyncio.run(
                guardrail.async_pre_call_hook(
                    None,
                    None,
                    {
                        "model": "task-youtube-summary",
                        "messages": [{"role": "user", "content": "https://youtu.be/dQw4w9WgXcQ"}],
                    },
                    "chat.completions",
                )
            )
        self.assertTrue(result["_youtube_summary_chunked"])
        self.assertEqual(result["messages"][0]["content"], "Reply with exactly: youtube-summary-chunked-placeholder")
        self.assertEqual(result["max_tokens"], 64)

    def test_post_call_rewrites_responses_payload_with_output_text(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-post", "post_call", True)
        response = {
            "object": "response",
            "id": "resp_123",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "Video: dQw4w9WgXcQ | Transcript: English | Captions: manual", "annotations": []}],
                }
            ],
        }
        result = asyncio.run(
            guardrail.async_post_call_success_hook(
                {"model": "task-youtube-summary"},
                None,
                response,
            )
        )
        self.assertEqual(result["id"], "resp_123")
        self.assertEqual(result["output_text"], "Video: dQw4w9WgXcQ | Transcript: English | Captions: manual")

    def test_post_call_chunked_returns_internal_final_response(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-post", "post_call", True)
        transcript_meta = {
            "video_id": "dQw4w9WgXcQ",
            "transcript_language": "English",
            "transcript_language_code": "en",
            "caption_type": "manual",
            "was_translated": False,
            "token_estimate": 30000,
            "segments": [{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
        }
        internal_final = {
            "object": "response",
            "id": "resp_final",
            "previous_response_id": None,
            "usage": {"input_tokens_details": {"cached_tokens": 0}},
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "chunked final summary", "annotations": []}],
                }
            ],
        }
        with patch.object(youtube_summary_guardrail, "_run_chunked_summary", AsyncMock(return_value=internal_final)):
            result = asyncio.run(
                guardrail.async_post_call_success_hook(
                    {
                        "model": "task-youtube-summary",
                        "_youtube_summary_chunked": True,
                        "_youtube_summary_focus_request": "",
                        "_youtube_summary_transcript_meta": transcript_meta,
                        "api_base": "http://127.0.0.1:8126/v1",
                        "api_key": "dummy",
                    },
                    None,
                    {"object": "response", "id": "resp_placeholder"},
                )
            )
        self.assertEqual(result["id"], "resp_final")
        self.assertEqual(result["output_text"], "chunked final summary")

    def test_run_chunked_summary_uses_env_fallbacks_when_callback_data_lacks_provider_fields(self):
        transcript = youtube_summary_guardrail.TranscriptFetchResult(
            video_id="dQw4w9WgXcQ",
            transcript_text="[00:00] hello world",
            transcript_language="English",
            transcript_language_code="en",
            caption_type="manual",
            was_translated=False,
            token_estimate=30000,
            segments=[{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
        )
        captured = []

        async def fake_post(api_base, api_key, payload):
            captured.append((api_base, api_key, payload["model"]))
            return {
                "object": "response",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": "ok", "annotations": []}],
                    }
                ],
            }

        with patch.dict(
            youtube_summary_guardrail.os.environ,
            {"LLMSTER_DEEP_API_BASE": "http://deep.example/v1", "LLMSTER_DEEP_MODEL": "openai/deep-model"},
            clear=False,
        ):
            with patch.object(youtube_summary_guardrail, "_post_responses", side_effect=fake_post):
                result = asyncio.run(
                    youtube_summary_guardrail._run_chunked_summary(
                        {"model": "task-youtube-summary", "api_key": "dummy", "_youtube_summary_focus_request": ""},
                        transcript,
                    )
                )
        self.assertEqual(result["object"], "response")
        self.assertTrue(captured)
        self.assertEqual(captured[0][0], "http://deep.example/v1")
        self.assertEqual(captured[0][2], "openai/deep-model")


if __name__ == "__main__":
    unittest.main()
