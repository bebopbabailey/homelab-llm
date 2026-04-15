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

    def test_defaults_chatgpt5_to_open_terminal_when_unset(self):
        terminal_id = self.middleware._default_chatgpt5_terminal_id(
            model_id="chatgpt-5",
            terminal_id=None,
            tool_ids=None,
            payload_tools=None,
            available_terminal_ids=["open-terminal"],
        )
        self.assertEqual(terminal_id, "open-terminal")

    def test_default_uses_selected_model_id_even_if_task_model_differs(self):
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

    def test_chatgpt5_terminal_selector_uses_selected_model_id(self):
        selector_model_id = self.middleware._chatgpt5_terminal_tool_selector_model_id(
            "chatgpt-5",
            "task-meta",
            {"list_files": {"type": "terminal", "spec": {"name": "list_files"}}},
        )
        self.assertEqual(selector_model_id, "chatgpt-5")

    def test_other_selector_cases_keep_task_model(self):
        self.assertEqual(
            self.middleware._chatgpt5_terminal_tool_selector_model_id(
                "main",
                "task-meta",
                {"list_files": {"type": "terminal", "spec": {"name": "list_files"}}},
            ),
            "task-meta",
        )
        self.assertEqual(
            self.middleware._chatgpt5_terminal_tool_selector_model_id(
                "chatgpt-5",
                "task-meta",
                {"grep_search": {"type": "mcp", "spec": {"name": "grep_search"}}},
            ),
            "task-meta",
        )

    def test_chatgpt5_terminal_selector_prompt_hardens_exact_tool_names(self):
        prompt = self.middleware._chatgpt5_terminal_tool_selector_prompt(
            "chatgpt-5",
            {"list_files": {"type": "terminal", "spec": {"name": "list_files"}}},
            "Available Tools: [...]",
        )
        self.assertIn("Use only exact tool names", prompt)
        self.assertIn("Never invent aliases such as `shell`", prompt)

    def test_non_chatgpt5_prompt_hardening_is_unchanged(self):
        prompt = self.middleware._chatgpt5_terminal_tool_selector_prompt(
            "main",
            {"list_files": {"type": "terminal", "spec": {"name": "list_files"}}},
            "Available Tools: [...]",
        )
        self.assertEqual(prompt, "Available Tools: [...]")

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
