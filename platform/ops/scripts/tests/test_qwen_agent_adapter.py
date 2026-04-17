import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "qwen_agent_adapter.py"
SPEC = importlib.util.spec_from_file_location("qwen_agent_adapter", MODULE_PATH)
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


class QwenAgentAdapterTests(unittest.TestCase):
    def test_convert_openai_tools_to_qwen_functions(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_virtual_file",
                    "description": "Read a file.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }
        ]
        functions = adapter.convert_openai_tools_to_qwen_functions(tools)
        self.assertEqual(functions[0]["name"], "read_virtual_file")

    def test_convert_openai_tools_rejects_non_function_tools(self):
        with self.assertRaises(ValueError):
            adapter.convert_openai_tools_to_qwen_functions([{"type": "web_search"}])

    def test_run_turn_returns_assistant_text_when_no_call_and_not_required(self):
        inst = object.__new__(adapter.QwenAgentAdapter)
        inst.use_raw_api = False
        inst._chat_once = lambda **_: [{"role": "assistant", "content": "plain text"}]
        result = inst.run_turn(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            must_call=False,
        )
        self.assertEqual(result.status, "assistant_text")
        self.assertEqual(result.assistant_text, "plain text")

    def test_run_turn_enforces_must_call(self):
        inst = object.__new__(adapter.QwenAgentAdapter)
        inst.use_raw_api = False
        inst._chat_once = lambda **_: [{"role": "assistant", "content": "plain text"}]
        result = inst.run_turn(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            must_call=True,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("must_call", result.error)

    def test_run_turn_normalizes_function_call(self):
        inst = object.__new__(adapter.QwenAgentAdapter)
        inst.use_raw_api = True
        inst._chat_once = lambda **_: [
            {
                "role": "assistant",
                "content": "",
                "function_call": {"name": "noop", "arguments": '{"value":"x"}'},
                "extra": {"function_id": "abc"},
            }
        ]
        result = inst.run_turn(
            messages=[{"role": "user", "content": "hi"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "noop",
                        "description": "desc",
                        "parameters": {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]},
                    },
                }
            ],
            must_call=True,
            allowed_function_names=["noop"],
        )
        self.assertEqual(result.status, "function_call")
        assert result.function_call is not None
        self.assertEqual(result.function_call.arguments["value"], "x")
        self.assertEqual(result.function_call.function_id, "abc")

    def test_run_turn_rejects_raw_markup(self):
        inst = object.__new__(adapter.QwenAgentAdapter)
        inst.use_raw_api = False
        inst._chat_once = lambda **_: [{"role": "assistant", "content": "<tool_call>bad</tool_call>"}]
        result = inst.run_turn(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            must_call=False,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("raw tool markup", result.error)


if __name__ == "__main__":
    unittest.main()
