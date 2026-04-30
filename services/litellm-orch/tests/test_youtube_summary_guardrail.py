import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from litellm.types.llms.openai import ResponsesAPIResponse

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


class DummyToolText:
    def __init__(self, text):
        self.text = text


class DummyToolResult:
    def __init__(self, *, text, is_error=False):
        self.content = [DummyToolText(text)]
        self.isError = is_error


class DummyTransportContext:
    async def __aenter__(self):
        return object(), object(), lambda: None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySessionContext:
    def __init__(self, result):
        self._result = result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def initialize(self):
        return None

    async def call_tool(self, *_args, **_kwargs):
        return self._result


class TestYouTubeSummaryHelpers(unittest.TestCase):
    def test_loader_style_double_import_shares_request_context_state(self):
        module_a = _load_module(
            REPO_ROOT / "services/litellm-orch/config/youtube_summary_guardrail.py",
            "youtube_summary_guardrail_loader_a",
        )
        module_b = _load_module(
            REPO_ROOT / "services/litellm-orch/config/youtube_summary_guardrail.py",
            "youtube_summary_guardrail_loader_b",
        )
        self.assertIs(module_a._REQUEST_CONTEXTS, module_b._REQUEST_CONTEXTS)
        self.assertIs(module_a._LOCK, module_b._LOCK)

    def test_extract_url_and_focus_request(self):
        url, video_id, focus = youtube_summary_guardrail._extract_url_and_focus_request(
            "https://youtu.be/dQw4w9WgXcQ focus on claims and examples"
        )
        self.assertEqual(url, "https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(video_id, "dQw4w9WgXcQ")
        self.assertEqual(focus, "focus on claims and examples")

    def test_extract_document_id_and_recover_from_messages(self):
        self.assertEqual(
            youtube_summary_guardrail._extract_document_id("Document: youtube:dQw4w9WgXcQ"),
            "youtube:dqw4w9wgxcq",
        )
        messages = [
            {"role": "user", "content": "https://youtu.be/dQw4w9WgXcQ"},
            {
                "role": "assistant",
                "content": "Video: dQw4w9WgXcQ | Document: youtube:dQw4w9WgXcQ | Transcript: English | Captions: manual",
            },
            {"role": "user", "content": "What was the core workflow?"},
        ]
        self.assertEqual(
            youtube_summary_guardrail._recover_document_id_from_messages(messages),
            "youtube:dqw4w9wgxcq",
        )

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

    def test_parse_transcript_tool_error(self):
        status, detail = youtube_summary_guardrail._parse_transcript_tool_error(
            "Error executing tool youtube.transcript: no_transcript: no usable transcript"
        )
        self.assertEqual(status, 404)
        self.assertEqual(detail, "no usable transcript")

    def test_followup_messages_fail_closed_when_no_excerpts_exist(self):
        messages = youtube_summary_guardrail._build_followup_retrieval_messages("What was the core workflow?", [])
        self.assertIn("No transcript excerpts were retrieved", messages[-1]["content"])

    def test_fetch_transcript_uses_structured_mcp_payload(self):
        payload = {
            "video_id": "dQw4w9WgXcQ",
            "source_url": "https://youtu.be/dQw4w9WgXcQ",
            "language": "German",
            "language_code": "de",
            "caption_type": "manual",
            "transcript_text": "[00:00] Hallo Welt",
            "segments": [{"text": "Hallo Welt", "start": 0.0, "duration": 1.0, "timestamp_label": "00:00"}],
        }
        with patch.object(youtube_summary_guardrail, "streamable_http_client", return_value=DummyTransportContext()), patch.object(
            youtube_summary_guardrail,
            "ClientSession",
            side_effect=lambda *args, **kwargs: DummySessionContext(DummyToolResult(text=__import__("json").dumps(payload))),
        ):
            result = asyncio.run(youtube_summary_guardrail._fetch_transcript("https://youtu.be/dQw4w9WgXcQ"))
        self.assertEqual(result.source_url, "https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(result.transcript_language_code, "de")
        self.assertEqual(result.segments[0]["timestamp"], "00:00")

    def test_fetch_transcript_maps_mcp_tool_error_to_http(self):
        with patch.object(youtube_summary_guardrail, "streamable_http_client", return_value=DummyTransportContext()), patch.object(
            youtube_summary_guardrail,
            "ClientSession",
            side_effect=lambda *args, **kwargs: DummySessionContext(
                DummyToolResult(text="Error executing tool youtube.transcript: no_transcript: no usable transcript", is_error=True)
            ),
        ):
            with self.assertRaises(HTTPException) as excinfo:
                asyncio.run(youtube_summary_guardrail._fetch_transcript("https://youtu.be/dQw4w9WgXcQ"))
        self.assertEqual(excinfo.exception.status_code, 404)

    def test_memory_api_headers_only_attach_bearer_for_write_routes(self):
        with patch.dict(youtube_summary_guardrail.os.environ, {"MEMORY_API_BEARER_TOKEN": "secret-token"}, clear=False):
            self.assertEqual(
                youtube_summary_guardrail._memory_api_headers("/v1/memory/upsert"),
                {"Authorization": "Bearer secret-token"},
            )
            self.assertEqual(youtube_summary_guardrail._memory_api_headers("/v1/memory/search"), {})


class TestYouTubeSummaryGuardrail(unittest.TestCase):
    def test_pre_call_initial_responses_sets_prompt_id_and_prompt_variables(self):
        transcript = youtube_summary_guardrail.TranscriptFetchResult(
            video_id="dQw4w9WgXcQ",
            source_url="https://youtu.be/dQw4w9WgXcQ",
            transcript_text="[00:00] hello world",
            transcript_language="English",
            transcript_language_code="en",
            caption_type="manual",
            was_translated=False,
            token_estimate=1200,
            segments=[{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
        )
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(youtube_summary_guardrail, "_fetch_transcript", AsyncMock(return_value=transcript)), patch.object(
            youtube_summary_guardrail,
            "_upsert_transcript_document",
            AsyncMock(return_value="youtube:dQw4w9WgXcQ"),
        ) as upsert_mock:
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
        upsert_mock.assert_awaited_once()
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

    def test_pre_call_followup_passthroughs_without_refetch_when_mapping_is_missing(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(youtube_summary_guardrail, "_fetch_transcript", AsyncMock()) as fetch_mock, patch.object(
            youtube_summary_guardrail,
            "_resolve_response_mapping",
            AsyncMock(return_value=None),
        ):
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

    def test_pre_call_followup_rehydrates_from_retrieval_mapping(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(
            youtube_summary_guardrail,
            "_resolve_response_mapping",
            AsyncMock(return_value={"document_id": "youtube:dQw4w9WgXcQ"}),
        ), patch.object(
            youtube_summary_guardrail,
            "_search_document",
            AsyncMock(return_value=[{"text": "retrieved transcript slice", "spans": {"timestamp_label": "00:42"}}]),
        ):
            result = asyncio.run(
                guardrail.async_pre_call_hook(
                    None,
                    None,
                    {
                        "model": "task-youtube-summary",
                        "previous_response_id": "resp_123",
                        "input": [{"role": "user", "content": "What was the core workflow?"}],
                    },
                    "responses",
                )
            )
        self.assertNotIn("previous_response_id", result)
        self.assertIn("input", result)
        self.assertIn("retrieved transcript slice", result["input"][-1]["content"])
        self.assertFalse(result["stream"])

    def test_pre_call_chat_followup_recovers_document_id_from_history(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(
            youtube_summary_guardrail,
            "_search_document",
            AsyncMock(return_value=[{"text": "retrieved transcript slice", "spans": {"timestamp_label": "00:42"}}]),
        ):
            result = asyncio.run(
                guardrail.async_pre_call_hook(
                    None,
                    None,
                    {
                        "model": "task-youtube-summary",
                        "messages": [
                            {"role": "user", "content": "https://youtu.be/dQw4w9WgXcQ"},
                            {
                                "role": "assistant",
                                "content": (
                                    "Video: dQw4w9WgXcQ | Document: youtube:dQw4w9WgXcQ | "
                                    "Transcript: English | Captions: manual"
                                ),
                            },
                            {"role": "user", "content": "What was the core workflow?"},
                        ],
                    },
                    "chat.completions",
                )
            )
        self.assertEqual(result["messages"][0]["role"], "system")
        self.assertIn("retrieved transcript slice", result["messages"][-1]["content"])
        self.assertFalse(result["stream"])

    def test_pre_call_chunked_uses_placeholder(self):
        transcript = youtube_summary_guardrail.TranscriptFetchResult(
            video_id="dQw4w9WgXcQ",
            source_url="https://youtu.be/dQw4w9WgXcQ",
            transcript_text="[00:00] hello world",
            transcript_language="English",
            transcript_language_code="en",
            caption_type="manual",
            was_translated=False,
            token_estimate=youtube_summary_guardrail.SINGLE_PASS_TRANSCRIPT_TOKENS + 1,
            segments=[{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
        )
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-pre", "pre_call", True)
        with patch.object(youtube_summary_guardrail, "_fetch_transcript", AsyncMock(return_value=transcript)), patch.object(
            youtube_summary_guardrail,
            "_upsert_transcript_document",
            AsyncMock(return_value="youtube:dQw4w9WgXcQ"),
        ) as upsert_mock:
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
        upsert_mock.assert_awaited_once()
        self.assertTrue(result["_youtube_summary_chunked"])
        self.assertEqual(result["messages"][0]["content"], "Reply with exactly: youtube-summary-chunked-placeholder")
        self.assertEqual(result["max_tokens"], 64)
        self.assertIn(id(result), youtube_summary_guardrail._REQUEST_CONTEXTS)

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
                    "content": [{"type": "output_text", "text": "Video: dQw4w9WgXcQ | Document: youtube:dQw4w9WgXcQ | Transcript: English | Captions: manual", "annotations": []}],
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
        self.assertEqual(result["output_text"], "Video: dQw4w9WgXcQ | Document: youtube:dQw4w9WgXcQ | Transcript: English | Captions: manual")

    def test_post_call_chunked_returns_internal_final_response(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-post", "post_call", True)
        transcript_meta = {
            "video_id": "dQw4w9WgXcQ",
            "source_url": "https://youtu.be/dQw4w9WgXcQ",
            "transcript_language": "English",
            "transcript_language_code": "en",
            "caption_type": "manual",
            "was_translated": False,
            "token_estimate": 30000,
            "segments": [{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
            "document_id": "youtube:dQw4w9WgXcQ",
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
        with patch.object(youtube_summary_guardrail, "_run_chunked_summary", AsyncMock(return_value=internal_final)), patch.object(
            youtube_summary_guardrail,
            "_upsert_response_mapping",
            AsyncMock(),
        ) as upsert_map_mock:
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
        upsert_map_mock.assert_awaited_once_with("resp_placeholder", "youtube:dQw4w9WgXcQ", "indexed_long")
        self.assertEqual(result["id"], "resp_placeholder")
        self.assertEqual(result["output_text"], "chunked final summary")

    def test_post_call_chunked_rewrites_typed_responses_object(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-post", "post_call", True)
        transcript_meta = {
            "video_id": "dQw4w9WgXcQ",
            "source_url": "https://youtu.be/dQw4w9WgXcQ",
            "transcript_language": "English",
            "transcript_language_code": "en",
            "caption_type": "manual",
            "was_translated": False,
            "token_estimate": 30000,
            "segments": [{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
            "document_id": "youtube:dQw4w9WgXcQ",
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
                    "content": [{"type": "output_text", "text": "typed chunked final summary", "annotations": []}],
                }
            ],
        }
        typed_placeholder = ResponsesAPIResponse.model_validate(
            {
                "id": "resp_placeholder",
                "created_at": 1,
                "model": "task-youtube-summary",
                "object": "response",
                "output": [
                    {
                        "id": "msg_placeholder",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": "youtube-summary-chunked-placeholder", "annotations": []}],
                    }
                ],
                "parallel_tool_calls": True,
                "temperature": 0.0,
                "tool_choice": "auto",
                "tools": [],
                "top_p": 1.0,
                "max_output_tokens": 64,
                "status": "completed",
                "text": {"format": {"type": "text"}},
                "truncation": "auto",
            }
        )
        with patch.object(youtube_summary_guardrail, "_run_chunked_summary", AsyncMock(return_value=internal_final)), patch.object(
            youtube_summary_guardrail,
            "_upsert_response_mapping",
            AsyncMock(),
        ) as upsert_map_mock:
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
                    typed_placeholder,
                )
            )
        upsert_map_mock.assert_awaited_once_with("resp_placeholder", "youtube:dQw4w9WgXcQ", "indexed_long")
        self.assertIsInstance(result, ResponsesAPIResponse)
        self.assertEqual(result.id, "resp_placeholder")
        self.assertEqual(result.output_text, "typed chunked final summary")

    def test_post_call_chunked_uses_saved_request_context_when_custom_fields_are_missing(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-post", "post_call", True)
        data = {"model": "task-youtube-summary"}
        youtube_summary_guardrail._REQUEST_CONTEXTS[id(data)] = {
            "chunked": True,
            "focus_request": "focus on examples",
            "transcript_meta": {
                "video_id": "dQw4w9WgXcQ",
                "source_url": "https://youtu.be/dQw4w9WgXcQ",
                "transcript_language": "English",
                "transcript_language_code": "en",
                "caption_type": "manual",
                "was_translated": False,
                "token_estimate": 30000,
                "segments": [{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
                "document_id": "youtube:dQw4w9WgXcQ",
            },
            "model": "task-youtube-summary",
            "api_base": None,
            "api_key": "dummy",
        }
        with patch.object(
            youtube_summary_guardrail,
            "_run_chunked_summary",
            AsyncMock(
                return_value={
                    "object": "response",
                    "id": "resp_final",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": "chunked final summary", "annotations": []}],
                        }
                    ],
                }
            ),
        ), patch.object(
            youtube_summary_guardrail,
            "_upsert_response_mapping",
            AsyncMock(),
        ):
            result = asyncio.run(
                guardrail.async_post_call_success_hook(
                    data,
                    None,
                    {"object": "response", "id": "resp_placeholder"},
                )
            )
        self.assertEqual(result["output_text"], "chunked final summary")

    def test_post_call_chunked_uses_saved_request_context_when_model_is_rewritten_to_provider(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-post", "post_call", True)
        data = {"model": "openai/llmster-gpt-oss-120b-mxfp4-gguf"}
        youtube_summary_guardrail._REQUEST_CONTEXTS[id(data)] = {
            "chunked": True,
            "focus_request": "",
            "transcript_meta": {
                "video_id": "dQw4w9WgXcQ",
                "source_url": "https://youtu.be/dQw4w9WgXcQ",
                "transcript_language": "English",
                "transcript_language_code": "en",
                "caption_type": "manual",
                "was_translated": False,
                "token_estimate": 30000,
                "segments": [{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
                "document_id": "youtube:dQw4w9WgXcQ",
            },
            "model": "task-youtube-summary",
            "api_base": "http://127.0.0.1:8126/v1",
            "api_key": "dummy",
        }
        with patch.object(
            youtube_summary_guardrail,
            "_run_chunked_summary",
            AsyncMock(
                return_value={
                    "object": "response",
                    "id": "resp_final_provider",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": "provider rewrite fixed", "annotations": []}],
                        }
                    ],
                }
            ),
        ), patch.object(
            youtube_summary_guardrail,
            "_upsert_response_mapping",
            AsyncMock(),
        ):
            result = asyncio.run(
                guardrail.async_post_call_success_hook(
                    data,
                    None,
                    {"object": "response", "id": "resp_placeholder"},
                )
            )
        self.assertEqual(result["output_text"], "provider rewrite fixed")

    def test_run_chunked_summary_uses_env_fallbacks_when_callback_data_lacks_provider_fields(self):
        transcript = youtube_summary_guardrail.TranscriptFetchResult(
            video_id="dQw4w9WgXcQ",
            source_url="https://youtu.be/dQw4w9WgXcQ",
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
        self.assertEqual(captured[0][2], "deep-model")

    def test_post_call_direct_response_upserts_response_mapping(self):
        guardrail = youtube_summary_guardrail.YouTubeSummaryGuardrail("youtube-summary-post", "post_call", True)
        response = {
            "object": "response",
            "id": "resp_short",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "short summary", "annotations": []}],
                }
            ],
        }
        with patch.object(
            youtube_summary_guardrail,
            "_upsert_response_mapping",
            AsyncMock(),
        ) as upsert_map_mock:
            result = asyncio.run(
                guardrail.async_post_call_success_hook(
                    {
                        "model": "task-youtube-summary",
                        "_youtube_summary_transcript_meta": {
                            "video_id": "dQw4w9WgXcQ",
                            "source_url": "https://youtu.be/dQw4w9WgXcQ",
                            "transcript_language": "English",
                            "transcript_language_code": "en",
                            "caption_type": "manual",
                            "was_translated": False,
                            "token_estimate": 1000,
                            "segments": [{"timestamp": "00:00", "text": "hello world", "start": 0.0, "duration": 1.0}],
                            "document_id": "youtube:dQw4w9WgXcQ",
                        },
                    },
                    None,
                    response,
                )
            )
        upsert_map_mock.assert_awaited_once_with("resp_short", "youtube:dQw4w9WgXcQ", "direct_short")
        self.assertEqual(result["output_text"], "short summary")


if __name__ == "__main__":
    unittest.main()
