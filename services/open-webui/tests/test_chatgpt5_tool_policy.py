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


class ChatGpt5ToolPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.misc = _load_module("open_webui/utils/misc.py", "open_webui_misc_runtime")
        cls.middleware = _load_module(
            "open_webui/utils/middleware.py", "open_webui_middleware_runtime"
        )

    def test_convert_output_prefers_fc_id_for_follow_up_messages(self):
        output = [
            {
                "type": "function_call",
                "id": "fc_123",
                "call_id": "call_abc",
                "name": "open-terminal-mcp-ro_list_files",
                "arguments": "{\"path\":\".\"}",
            },
            {
                "type": "function_call_output",
                "id": "fco_1",
                "call_id": "call_abc",
                "output": [{"type": "input_text", "text": "[]"}],
            },
        ]

        messages = self.misc.convert_output_to_messages(output, raw=True)

        self.assertEqual(messages[0]["tool_calls"][0]["id"], "fc_123")
        self.assertEqual(messages[1]["tool_call_id"], "fc_123")

    def test_chatgpt5_native_lane_is_readonly_mcp_only(self):
        allowed = self.middleware._chatgpt5_native_readonly_lane(
            "chatgpt-5",
            {"params": {"function_calling": "native"}},
            payload_tools=None,
        )
        denied = self.middleware._chatgpt5_native_readonly_lane(
            "chatgpt-5",
            {"params": {"function_calling": "default"}},
            payload_tools=None,
        )

        self.assertTrue(allowed)
        self.assertFalse(denied)

    def test_allowed_tool_names_match_readonly_mcp_subset(self):
        self.assertEqual(
            set(self.middleware.CHATGPT5_ALLOWED_TOOL_NAMES),
            {
                "open-terminal-mcp-ro_glob_search",
                "open-terminal-mcp-ro_grep_search",
                "open-terminal-mcp-ro_health_check",
                "open-terminal-mcp-ro_list_files",
                "open-terminal-mcp-ro_read_file",
            },
        )

    def test_unavailable_tool_message_lists_allowed_tools(self):
        message = self.middleware._unavailable_tool_message(
            "shell",
            list(self.middleware.CHATGPT5_ALLOWED_TOOL_NAMES),
        )

        self.assertIn("shell", message)
        self.assertIn("open-terminal-mcp-ro_read_file", message)
        self.assertIn("not available", message)


if __name__ == "__main__":
    unittest.main()
