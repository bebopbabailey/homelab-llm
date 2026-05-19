import asyncio
import json
import re
import unittest
import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from litellm.integrations.dotprompt.prompt_manager import PromptManager
from litellm.types.utils import TranscriptionResponse

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


transcribe_utils = _load_module(
    REPO_ROOT / "services/litellm-orch/config/transcribe_utils.py",
    "transcribe_utils",
)
sys.modules["config.transcribe_utils"] = transcribe_utils
transcribe_guardrail = _load_module(
    REPO_ROOT / "services/litellm-orch/config/transcribe_guardrail.py",
    "transcribe_guardrail",
)
strip_wrappers = transcribe_utils.strip_wrappers
prepare_transcript_text = transcribe_utils.prepare_transcript_text
prompt_manager = PromptManager(
    prompt_directory=str(REPO_ROOT / "services/litellm-orch/prompts")
)


class TestTranscribeBaseline(unittest.TestCase):
    def test_pre_call_task_transcribe_sets_prompt_id_and_keeps_alias_model(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "messages": [{"role": "user", "content": "um i i think this should probably work maybe yes"}],
                    "prompt_variables": {},
                },
                "chat.completions",
            )
        )

        self.assertEqual(result["model"], "task-transcribe")
        self.assertEqual(result["prompt_id"], "task-transcribe")
        self.assertFalse(result["stream"])
        self.assertEqual(result["max_tokens"], 8192)
        self.assertEqual(
            result["prompt_variables"]["user_message"],
            "um i i think this should probably work maybe yes",
        )
        self.assertEqual(result["prompt_variables"]["audience"], "")
        self.assertEqual(result["prompt_variables"]["tone"], "")

    def test_pre_call_task_transcribe_responses_uses_input_and_min_budget(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "input": [{"role": "user", "content": "um i i think this should probably work maybe yes"}],
                    "max_output_tokens": 128,
                    "prompt_variables": {},
                },
                "responses",
            )
        )
        self.assertEqual(result["prompt_id"], "task-transcribe")
        self.assertEqual(result["max_output_tokens"], 128)
        self.assertEqual(result["prompt_variables"]["user_message"], "um i i think this should probably work maybe yes")

    def test_pre_call_task_transcribe_prompt_variables_shape_single_prompt(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "messages": [{"role": "user", "content": "uh okay this is kind of sudden but it matters a lot actually"}],
                    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
                },
                "chat.completions",
            )
        )

        self.assertEqual(result["model"], "task-transcribe")
        self.assertEqual(result["_transcribe_text_cleanup_alias"], "task-transcribe")
        self.assertNotIn("_transcribe_mode", result)
        self.assertEqual(result["prompt_id"], "task-transcribe")
        self.assertFalse(result["stream"])
        self.assertEqual(result["max_tokens"], 8192)
        self.assertEqual(
            result["prompt_variables"]["user_message"],
            "uh okay this is kind of sudden but it matters a lot actually",
        )
        self.assertEqual(result["prompt_variables"]["audience"], "internal notes")
        self.assertEqual(result["prompt_variables"]["tone"], "lightly polished")

    def test_pre_call_task_transcribe_uses_default_when_output_budget_omitted(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "input": [{"role": "user", "content": "uh okay this matters"}],
                    "prompt_variables": {"audience": "internal notes"},
                },
                "responses",
            )
        )

        self.assertEqual(result["model"], "task-transcribe")
        self.assertEqual(result["prompt_id"], "task-transcribe")
        self.assertEqual(result["max_output_tokens"], 8192)
        self.assertEqual(result["prompt_variables"]["tone"], "")

    def test_pre_call_audio_task_transcribe_routes_to_voice_stt(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "file": object(),
                    "language": "en",
                },
                "transcription",
            )
        )

        self.assertEqual(result["model"], "voice-stt")
        self.assertEqual(result["_transcribe_audio_cleanup_alias"], "task-transcribe")
        self.assertEqual(result["_transcribe_audio_original_model"], "task-transcribe")
        self.assertEqual(result["_transcribe_audio_max_output_tokens"], 8192)
        self.assertEqual(result["language"], "en")
        self.assertNotIn("prompt_id", result)

    def test_pre_call_audio_task_transcribe_prompt_variables_route_to_voice_stt(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "file": object(),
                    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
                },
                "transcription",
            )
        )

        self.assertEqual(result["model"], "voice-stt")
        self.assertEqual(result["_transcribe_audio_cleanup_alias"], "task-transcribe")
        self.assertNotIn("_transcribe_mode", result)
        self.assertEqual(result["_transcribe_audio_max_output_tokens"], 8192)

    def test_pre_call_audio_task_transcribe_preserves_output_token_override(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "file": object(),
                    "max_output_tokens": "1024",
                },
                "transcription",
            )
        )

        self.assertEqual(result["model"], "voice-stt")
        self.assertNotIn("max_output_tokens", result)
        self.assertEqual(result["_transcribe_audio_max_output_tokens"], 1024)

    def test_pre_call_audio_task_transcribe_preserves_prompt_variables(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "file": object(),
                    "prompt_variables": json.dumps(
                        {"audience": "internal notes", "tone": "lightly polished"}
                    ),
                },
                "transcription",
            )
        )

        self.assertEqual(result["model"], "voice-stt")
        self.assertNotIn("prompt_variables", result)
        self.assertEqual(
            result["_transcribe_audio_prompt_variables"],
            {"audience": "internal notes", "tone": "lightly polished"},
        )
        self.assertNotIn("_transcribe_mode", result)

    def test_transcribe_prompt_renders_without_model_override(self):
        pre_guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        request = asyncio.run(
            pre_guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "messages": [{"role": "user", "content": "um i i think this should probably work maybe yes"}],
                    "prompt_variables": {},
                },
                "chat.completions",
            )
        )

        rendered = prompt_manager.render(
            prompt_id=request["prompt_id"],
            prompt_variables=request["prompt_variables"],
        )
        self.assertIn("Transcript:\num i i think this should probably work maybe yes", rendered)
        self.assertIn("Audience: ", rendered)
        self.assertIn("Tone preference: ", rendered)

    def test_transcribe_prompt_renders_prompt_variables_in_single_template(self):
        pre_guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        request = asyncio.run(
            pre_guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "input": [{"role": "user", "content": "uh okay this matters"}],
                    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
                },
                "responses",
            )
        )
        rendered = prompt_manager.render(
            prompt_id=request["prompt_id"],
            prompt_variables=request["prompt_variables"],
        )
        self.assertEqual(request["prompt_id"], "task-transcribe")
        self.assertIn("Audience: internal notes", rendered)
        self.assertIn("Tone preference: lightly polished", rendered)
        self.assertIn("Transcript:\nuh okay this matters", rendered)

    def test_preprocess_preserves_apple_punctuation(self):
        raw = "And This is...\n\nThe 1st time, I'm really feeling crushed by the weight of.. The pile."
        prepared = prepare_transcript_text(raw)
        self.assertIn("This is...", prepared)
        self.assertIn("1st time,", prepared)
        self.assertIn("weight of..", prepared)
        self.assertIn("\n\n", prepared)

    def test_preprocess_trims_edge_whitespace_only(self):
        raw = "  it’s still a well-known thing — right?  "
        prepared = prepare_transcript_text(raw)
        self.assertEqual(prepared, "it’s still a well-known thing — right?")

    def test_postfilter_strips_wrappers(self):
        cases = [
            "**Cleaned Transcript**: Hello there.",
            "# Cleaned Transcript: Hello there.",
            "Cleaned Transcript: Hello there.",
        ]
        for output in cases:
            cleaned = strip_wrappers(output)
            self.assertEqual(cleaned, "Hello there.")

    def test_postfilter_keeps_real_content(self):
        output = "Cleaned transcript is hard."
        cleaned = strip_wrappers(output)
        self.assertEqual(cleaned, output)

    def test_postfilter_strips_quoted_wrapper(self):
        output = "\"Cleaned Transcript: quoted.\""
        cleaned = strip_wrappers(output)
        self.assertEqual(cleaned, "quoted.")

    def test_guardrail_uses_shared_helpers(self):
        self.assertIs(transcribe_guardrail._strip_wrappers, strip_wrappers)
        self.assertIs(transcribe_guardrail._preprocess_transcript, prepare_transcript_text)

    def test_post_call_strips_reasoning_and_wrappers(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-post", "post_call", True)
        response = {
            "choices": [
                {
                    "message": {
                        "content": "**Cleaned Transcript**: Hello there.",
                        "reasoning": "hidden",
                        "reasoning_content": "hidden",
                        "provider_specific_fields": {"reasoning": "hidden"},
                    }
                }
            ]
        }
        result = asyncio.run(guardrail.async_post_call_success_hook({"model": "task-transcribe"}, None, response))
        message = result["choices"][0]["message"]
        self.assertEqual(message["content"], "Hello there.")
        self.assertNotIn("reasoning", message)
        self.assertNotIn("reasoning_content", message)
        self.assertNotIn("provider_specific_fields", message)

    def test_post_call_rewrites_responses_payload(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-post", "post_call", True)
        response = {
            "object": "response",
            "output": [
                {
                    "type": "reasoning",
                    "content": [{"type": "reasoning_text", "text": "hidden"}],
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "**Cleaned Transcript**: Hello there.", "annotations": []}],
                },
            ],
            "reasoning": {"effort": "low"},
        }
        result = asyncio.run(guardrail.async_post_call_success_hook({"model": "task-transcribe"}, None, response))
        self.assertEqual(result["output"][0]["type"], "message")
        self.assertEqual(result["output"][0]["content"][0]["text"], "Hello there.")
        self.assertEqual(result["output_text"], "Hello there.")
        self.assertNotIn("reasoning", result)

    def test_post_call_rewrites_responses_with_internal_alias(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-post", "post_call", True)
        response = {
            "object": "response",
            "output_text": "**Cleaned Transcript**: Hello there.",
            "output": [],
        }
        result = asyncio.run(
            guardrail.async_post_call_success_hook(
                {"model": "task-transcribe", "_transcribe_text_cleanup_alias": "task-transcribe"},
                None,
                response,
            )
        )
        self.assertEqual(result["output_text"], "Hello there.")

    def test_audio_post_call_cleans_transcript_and_rewrites_minimal_payload(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-post", "post_call", True)
        response = TranscriptionResponse(text="um i think this works maybe yes")
        cleanup_body = {
            "id": "resp_clean",
            "object": "response",
            "output_text": "**Cleaned Transcript**: I think this works, maybe yes.",
            "output": [],
        }

        with patch.dict(
            transcribe_guardrail.os.environ,
            {
                "LLMSTER_FAST_API_BASE": "http://provider.test/v1",
                "LLMSTER_FAST_MODEL": "openai/provider-fast",
            },
        ), patch.object(transcribe_guardrail, "_post_responses", AsyncMock(return_value=cleanup_body)) as post:
            result = asyncio.run(
                guardrail.async_post_call_response_headers_hook(
                    {
                        "model": "voice-stt",
                        "_transcribe_audio_cleanup_alias": "task-transcribe",
                    },
                    None,
                    response,
                )
            )

        self.assertIsNone(result)
        self.assertEqual(response.model_dump(), {"id": "resp_clean", "output_text": "I think this works, maybe yes."})
        payload = post.await_args.args[2]
        self.assertEqual(post.await_args.args[0], "http://provider.test/v1")
        self.assertEqual(payload["model"], "provider-fast")
        self.assertEqual(payload["input"][-1]["content"], "Transcript:\num i think this works maybe yes")
        self.assertEqual(payload["max_output_tokens"], 8192)

    def test_audio_post_call_uses_prompt_variables_on_fast_lane(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-post", "post_call", True)
        response = TranscriptionResponse(text="uh okay this matters")
        cleanup_body = {
            "id": "resp_guided",
            "object": "response",
            "output_text": "Okay, this matters.",
            "output": [],
        }

        with patch.dict(
            transcribe_guardrail.os.environ,
            {
                "LLMSTER_FAST_API_BASE": "http://provider.test/v1",
                "LLMSTER_FAST_MODEL": "openai/provider-fast",
            },
        ), patch.object(transcribe_guardrail, "_post_responses", AsyncMock(return_value=cleanup_body)) as post:
            result = asyncio.run(
                guardrail.async_post_call_response_headers_hook(
                    {
                        "model": "voice-stt",
                        "_transcribe_audio_cleanup_alias": "task-transcribe",
                        "_transcribe_audio_prompt_variables": {
                            "audience": "internal notes",
                            "tone": "lightly polished",
                        },
                    },
                    None,
                    response,
                )
            )

        self.assertIsNone(result)
        self.assertEqual(response.model_dump(), {"id": "resp_guided", "output_text": "Okay, this matters."})
        payload = post.await_args.args[2]
        self.assertEqual(post.await_args.args[0], "http://provider.test/v1")
        self.assertEqual(payload["model"], "provider-fast")
        rendered_text = "\n".join(message["content"] for message in payload["input"])
        self.assertIn("internal notes", rendered_text)
        self.assertIn("lightly polished", rendered_text)
        self.assertIn("Transcript:\nuh okay this matters", rendered_text)
        self.assertEqual(payload["max_output_tokens"], 8192)

    def test_audio_post_call_empty_cleanup_falls_back_to_preprocessed_transcript(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-post", "post_call", True)
        response = TranscriptionResponse(text="okay?")
        cleanup_body = {
            "id": "resp_empty",
            "object": "response",
            "output_text": "",
            "output": [],
        }

        with patch.dict(
            transcribe_guardrail.os.environ,
            {
                "LLMSTER_FAST_API_BASE": "http://provider.test/v1",
                "LLMSTER_FAST_MODEL": "openai/provider-fast",
            },
        ), patch.object(transcribe_guardrail, "_post_responses", AsyncMock(return_value=cleanup_body)):
            result = asyncio.run(
                guardrail.async_post_call_response_headers_hook(
                    {
                        "model": "voice-stt",
                        "_transcribe_audio_cleanup_alias": "task-transcribe",
                    },
                    None,
                    response,
                )
            )

        self.assertIsNone(result)
        self.assertEqual(response.model_dump(), {"id": "resp_empty", "output_text": "okay?"})

    def test_audio_post_call_failure_does_not_return_raw_transcript(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-post", "post_call", True)
        response = TranscriptionResponse(text="raw sensitive transcript")

        with patch.object(
            transcribe_guardrail,
            "_clean_audio_transcript",
            AsyncMock(side_effect=RuntimeError("boom")),
        ), patch.object(transcribe_guardrail.logger, "exception") as log_exception:
            result = asyncio.run(
                guardrail.async_post_call_response_headers_hook(
                    {
                        "model": "voice-stt",
                        "_transcribe_audio_cleanup_alias": "task-transcribe",
                    },
                    None,
                    response,
                )
            )

        self.assertIsNone(result)
        log_exception.assert_called_once()
        self.assertRegex(response.model_dump()["id"], r"^resp_[0-9a-f]+$")
        self.assertEqual(response.model_dump()["output_text"], "")
        self.assertNotIn("raw sensitive transcript", str(response.model_dump()))

    def test_golden_output_matches_expectations(self):
        raw = (REPO_ROOT / "services/litellm-orch/tests/fixtures_transcribe_raw.txt").read_text().strip()
        expected = (REPO_ROOT / "services/litellm-orch/tests/fixtures_transcribe_expected.txt").read_text().strip()

        # 1) no headings/labels
        lowered = expected.lower()
        self.assertFalse(lowered.startswith("cleaned transcript"))
        self.assertFalse(lowered.startswith("here is the cleaned transcript"))

        # 2) begins with transcript content (not empty)
        self.assertTrue(len(expected) > 0)

        # 3) no additional words introduced beyond allowed disfluency removal
        def norm_tokens(text: str) -> list[str]:
            text = strip_wrappers(text)
            text = re.sub(r"[^\w\s']", " ", text.lower())
            text = re.sub(r"\s+", " ", text).strip()
            tokens = text.split()
            filler = {"um", "uh", "er", "ah", "hmm", "mm", "like"}
            filtered = []
            last = None
            for tok in tokens:
                if tok in filler:
                    continue
                if tok == last:
                    continue
                filtered.append(tok)
                last = tok
            return filtered

        raw_tokens = norm_tokens(raw)
        expected_tokens = norm_tokens(expected)
        self.assertTrue(set(expected_tokens).issubset(set(raw_tokens)))

        # 4) punctuation improved (should contain sentence-ending punctuation)
        self.assertRegex(expected, r"[.!?]")


if __name__ == "__main__":
    unittest.main()
