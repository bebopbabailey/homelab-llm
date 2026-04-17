import importlib.util
import sys
import unittest
from pathlib import Path


RUNTIME_ROOT = (
    Path.home()
    / "homelab-llm"
    / "layer-interface"
    / "open-webui"
    / ".venv"
    / "lib"
    / "python3.12"
    / "site-packages"
)

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))


def _load_module(rel_path: str, module_name: str):
    module_path = RUNTIME_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ChatGpt5TerminalDefaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.middleware = _load_module(
            "open_webui/utils/middleware.py", "open_webui_middleware_runtime"
        )
        cls.misc = _load_module("open_webui/utils/misc.py", "open_webui_misc_runtime")

    def test_chatgpt5_forces_text_only_and_clears_tooling(self):
        terminal_id, tool_ids, payload_tools, direct_tool_servers, params = (
            self.middleware._chatgpt5_force_text_only(
                "chatgpt-5",
                "open-terminal",
                ["server:mcp:open-terminal-mcp-ro"],
                [{"type": "function", "function": {"name": "x"}}],
                [{"id": "direct"}],
                {"function_calling": "native", "other": True},
            )
        )
        self.assertIsNone(terminal_id)
        self.assertIsNone(tool_ids)
        self.assertIsNone(payload_tools)
        self.assertIsNone(direct_tool_servers)
        self.assertNotIn("function_calling", params)
        self.assertTrue(params["other"])

    def test_other_models_do_not_force_text_only(self):
        terminal_id, tool_ids, payload_tools, direct_tool_servers, params = (
            self.middleware._chatgpt5_force_text_only(
                "main",
                "open-terminal",
                ["server:mcp:open-terminal-mcp-ro"],
                [{"type": "function", "function": {"name": "x"}}],
                [{"id": "direct"}],
                {"function_calling": "native", "other": True},
            )
        )
        self.assertEqual(terminal_id, "open-terminal")
        self.assertEqual(tool_ids, ["server:mcp:open-terminal-mcp-ro"])
        self.assertEqual(payload_tools[0]["function"]["name"], "x")
        self.assertEqual(direct_tool_servers[0]["id"], "direct")
        self.assertEqual(params["function_calling"], "native")

    def test_chatgpt5_does_not_default_back_to_open_terminal(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="chatgpt-5",
            terminal_id=None,
            tool_ids=None,
            payload_tools=None,
            available_terminal_ids=["open-terminal"],
        )
        self.assertIsNone(terminal_id)

    def test_default_terminal_helper_is_noop_for_other_models(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="main",
            terminal_id=None,
            tool_ids=None,
            payload_tools=None,
            available_terminal_ids=["open-terminal"],
        )
        self.assertIsNone(terminal_id)

    def test_normalizes_call_prefix_to_fc_prefix(self):
        tool_call_id = self.middleware._normalized_chatgpt5_tool_call_id(
            "call_abc123",
            "call_abc123",
        )
        self.assertEqual(tool_call_id, "fc_abc123")

    def test_convert_output_to_messages_uses_normalized_tool_call_ids(self):
        messages = self.misc.convert_output_to_messages(
            [
                {
                    "type": "function_call",
                    "id": "call_abc123",
                    "call_id": "call_abc123",
                    "name": "list_files",
                    "arguments": "{\"directory\":\".\"}",
                },
                {
                    "type": "function_call_output",
                    "id": "fco_1",
                    "call_id": "call_abc123",
                    "output": [{"type": "input_text", "text": "ok"}],
                },
            ],
            raw=True,
        )
        self.assertEqual(messages[0]["tool_calls"][0]["id"], "fc_abc123")
        self.assertEqual(messages[1]["tool_call_id"], "fc_abc123")

    def test_retries_known_chatgpt5_post_tool_gateway_failures(self):
        should_retry = self.middleware._should_retry_chatgpt5_post_tool_completion(
            model_id="chatgpt-5",
            attempt=0,
            exc=Exception(
                "502 Bad Gateway: Failed to convert provider response using format chain"
            ),
        )
        self.assertTrue(should_retry)

    def test_retry_limit_and_model_gate_are_narrow(self):
        self.assertFalse(
            self.middleware._should_retry_chatgpt5_post_tool_completion(
                model_id="chatgpt-5",
                attempt=2,
                exc=Exception("502 Bad Gateway"),
            )
        )
        self.assertFalse(
            self.middleware._should_retry_chatgpt5_post_tool_completion(
                model_id="main",
                attempt=0,
                exc=Exception("502 Bad Gateway"),
            )
        )


if __name__ == "__main__":
    unittest.main()
