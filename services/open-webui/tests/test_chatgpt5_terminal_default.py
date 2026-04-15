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

    def test_defaults_chatgpt5_to_open_terminal_when_unset(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="chatgpt-5",
            terminal_id=None,
            tool_ids=None,
            payload_tools=None,
            available_terminal_ids=["open-terminal"],
        )
        self.assertEqual(terminal_id, "open-terminal")

    def test_preserves_explicit_terminal_selection(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="chatgpt-5",
            terminal_id="custom-terminal",
            tool_ids=None,
            payload_tools=None,
            available_terminal_ids=["open-terminal", "custom-terminal"],
        )
        self.assertEqual(terminal_id, "custom-terminal")

    def test_explicit_tool_selection_disables_default(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="chatgpt-5",
            terminal_id=None,
            tool_ids=["server:mcp:open-terminal-mcp-ro"],
            payload_tools=None,
            available_terminal_ids=["open-terminal"],
        )
        self.assertIsNone(terminal_id)

    def test_payload_tools_disable_default(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="chatgpt-5",
            terminal_id=None,
            tool_ids=None,
            payload_tools=[{"type": "function", "function": {"name": "x"}}],
            available_terminal_ids=["open-terminal"],
        )
        self.assertIsNone(terminal_id)

    def test_other_models_are_unchanged(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="main",
            terminal_id=None,
            tool_ids=None,
            payload_tools=None,
            available_terminal_ids=["open-terminal"],
        )
        self.assertIsNone(terminal_id)

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
