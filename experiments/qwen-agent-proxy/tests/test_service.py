from pathlib import Path
import sys
import unittest


SERVICE_PATH = Path(__file__).resolve().parents[1] / "src" / "qwen_agent_proxy" / "service.py"
SRC_DIR = SERVICE_PATH.parents[1]
sys.path.insert(0, str(SRC_DIR))
from qwen_agent_proxy import service


class ServiceHelpersTests(unittest.TestCase):
    def test_parse_tool_choice_named_function(self):
        must_call, allowed, call_tools = service._parse_tool_choice(
            {"type": "function", "function": {"name": "noop"}}
        )
        self.assertTrue(must_call)
        self.assertEqual(allowed, ["noop"])
        self.assertTrue(call_tools)

    def test_parse_tool_choice_none_means_passthrough(self):
        must_call, allowed, call_tools = service._parse_tool_choice("none")
        self.assertFalse(must_call)
        self.assertIsNone(allowed)
        self.assertFalse(call_tools)

    def test_build_tool_call_response_shape(self):
        body = service._build_tool_call_response(
            public_model_id="shadow-model",
            function_name="noop",
            raw_arguments='{"value":"x"}',
            function_id="abc",
        )
        choice = body["choices"][0]
        self.assertEqual(choice["finish_reason"], "tool_calls")
        self.assertEqual(choice["message"]["tool_calls"][0]["function"]["name"], "noop")

    def test_build_text_response_shape(self):
        body = service._build_text_response(public_model_id="shadow-model", assistant_text="hello")
        choice = body["choices"][0]
        self.assertEqual(choice["finish_reason"], "stop")
        self.assertEqual(choice["message"]["content"], "hello")

    def test_model_info_payload_shape(self):
        settings = type(
            "S",
            (),
            {
                "public_model_id": "shadow-model",
                "backend_model": "openai/backend-model",
                "backend_base_url": "http://127.0.0.1:18134/v1",
                "default_max_tokens": 256,
            },
        )()
        payload = service._model_info_payload(settings)
        row = payload["data"][0]
        self.assertEqual(row["model_name"], "shadow-model")
        self.assertTrue(row["model_info"]["supports_function_calling"])
        self.assertEqual(row["litellm_params"]["api_base"], "http://127.0.0.1:18134/v1")


if __name__ == "__main__":
    unittest.main()
