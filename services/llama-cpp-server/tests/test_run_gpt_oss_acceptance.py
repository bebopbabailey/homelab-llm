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


if __name__ == "__main__":
    unittest.main()
