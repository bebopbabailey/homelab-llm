import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_gpt_oss_acceptance.py"
SPEC = importlib.util.spec_from_file_location(
    "run_gpt_oss_acceptance",
    SCRIPT,
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class RunGptOssAcceptanceTests(unittest.TestCase):
    def test_object_schema_is_strict(self):
        schema = mod._object_schema({"value": {"type": "string"}}, ["value"])
        self.assertEqual(schema["required"], ["value"])
        self.assertFalse(schema["additionalProperties"])

    def test_extract_responses_text_prefers_output_text(self):
        text = mod._extract_responses_text({"output_text": "hello"})
        self.assertEqual(text, "hello")

    def test_extract_responses_text_reads_output_chunks(self):
        body = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "hello"},
                        {"type": "output_text", "text": "-world"},
                    ]
                }
            ]
        }
        self.assertEqual(mod._extract_responses_text(body), "hello-world")

    def test_extract_cached_tokens_reads_usage_details(self):
        body = {"usage": {"input_tokens_details": {"cached_tokens": 42}}}
        self.assertEqual(mod._extract_cached_tokens(body), 42)
        self.assertIsNone(mod._extract_cached_tokens({}))

    def test_expect_responses_json_keys_reads_output_chunks(self):
        checker = mod._expect_responses_json_keys(["status"])
        good = {"output": [{"content": [{"type": "output_text", "text": "{\"status\":\"ok\"}"}]}]}
        bad = {"output": [{"content": [{"type": "output_text", "text": "nope"}]}]}
        self.assertTrue(checker(good))
        self.assertFalse(checker(bad))

    def test_raw_harmony_snippets_recurses_response_body(self):
        body = {"choices": [{"message": {"content": "<|channel|>final <|message|>done"}}]}
        self.assertEqual(mod._raw_harmony_snippets(body), ["<|channel|>final <|message|>done"])

    def test_raw_harmony_snippets_ignores_normal_response_body(self):
        body = {"choices": [{"message": {"content": "done"}}]}
        self.assertEqual(mod._raw_harmony_snippets(body), [])

    def test_expect_tool_call_requires_named_function(self):
        checker = mod._expect_tool_call("noop", "value")
        good = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "noop",
                                    "arguments": json.dumps({"value": "x"}),
                                }
                            }
                        ]
                    }
                }
            ]
        }
        bad = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "noop",
                                    "arguments": json.dumps({"wrong": "x"}),
                                }
                            }
                        ]
                    }
                }
            ]
        }
        self.assertTrue(checker(good))
        self.assertFalse(checker(bad))

    def test_profile_defaults_infer_deep_from_model_name(self):
        self.assertEqual(mod._profile_defaults("auto", "llmster-gpt-oss-120b-mxfp4-gguf"), (2, 4))
        self.assertEqual(mod._profile_defaults("auto", "llmster-gpt-oss-20b-mxfp4-gguf"), (4, 8))

    def test_run_responses_followup_records_ids_and_cached_tokens(self):
        replies = iter(
            [
                (
                    200,
                    {
                        "id": "resp_1",
                        "output": [{"content": [{"type": "output_text", "text": "followup-seed"}]}],
                        "usage": {"input_tokens_details": {"cached_tokens": 0}},
                    },
                    0.1,
                ),
                (
                    200,
                    {
                        "id": "resp_2",
                        "previous_response_id": "resp_1",
                        "output": [{"content": [{"type": "output_text", "text": "followup-ok"}]}],
                        "usage": {"input_tokens_details": {"cached_tokens": 7}},
                    },
                    0.2,
                ),
            ]
        )

        def fake_post(url, payload, api_key, timeout):
            return next(replies)

        original = mod._post
        try:
            mod._post = fake_post
            result = mod._run_responses_followup("http://example/v1/responses", "fast", 30.0, None)
        finally:
            mod._post = original

        self.assertTrue(result["ok"])
        self.assertTrue(result["initial_response_id_present"])
        self.assertTrue(result["previous_response_id_matches"])
        self.assertEqual(result["followup_cached_tokens"], 7)
        self.assertEqual(result["followup_text"], "followup-ok")


if __name__ == "__main__":
    unittest.main()
