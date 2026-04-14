import importlib.util
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/litellm-orch/config/qwen_toolcall_posthook.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


qwen_toolcall_posthook = _load_module(MODULE_PATH, "qwen_toolcall_posthook")
QwenToolcallPostHook = qwen_toolcall_posthook.QwenToolcallPostHook
_normalize_tool_payload = qwen_toolcall_posthook._normalize_tool_payload


class TestNormalizeToolPayload(unittest.TestCase):
    def test_preserves_full_name_and_arguments_shape(self):
        out = _normalize_tool_payload('{"name":"noop","arguments":{"value":"x"}}', None)
        self.assertEqual(out[0]["function"]["name"], "noop")
        self.assertEqual(json.loads(out[0]["function"]["arguments"]), {"value": "x"})

    def test_infers_single_declared_tool_name_for_args_only_shape(self):
        out = _normalize_tool_payload('{"value":"hello"}', "noop")
        self.assertEqual(out[0]["function"]["name"], "noop")
        self.assertEqual(json.loads(out[0]["function"]["arguments"]), {"value": "hello"})

    def test_rejects_args_only_shape_without_single_tool_name(self):
        self.assertIsNone(_normalize_tool_payload('{"value":"hello"}', None))


class TestQwenToolcallPostHook(unittest.IsolatedAsyncioTestCase):
    async def test_passthrough_when_tool_calls_already_present(self):
        hook = QwenToolcallPostHook(
            guardrail_name="qwen-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {"model": "main", "stream": False, "tool_choice": "auto", "tools": [{"function": {"name": "noop"}}]}
        response = {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{"type": "function", "function": {"name": "noop", "arguments": "{}"}}],
                    },
                }
            ]
        }
        out = await hook.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        self.assertEqual(out["choices"][0]["message"]["tool_calls"][0]["function"]["name"], "noop")

    async def test_normalizes_args_only_tool_block_for_main(self):
        hook = QwenToolcallPostHook(
            guardrail_name="qwen-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "main",
            "stream": False,
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "<tool_call>\n{\"value\":\"hello\"}\n</tool_call>",
                        "tool_calls": [],
                    },
                }
            ]
        }
        out = await hook.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        message = out["choices"][0]["message"]
        self.assertIsNone(message["content"])
        self.assertEqual(out["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(message["tool_calls"][0]["function"]["name"], "noop")
        self.assertEqual(json.loads(message["tool_calls"][0]["function"]["arguments"]), {"value": "hello"})

    async def test_passthrough_for_non_main(self):
        hook = QwenToolcallPostHook(
            guardrail_name="qwen-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "fast",
            "stream": False,
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "<tool_call>\n{\"value\":\"hello\"}\n</tool_call>",
                        "tool_calls": [],
                    },
                }
            ]
        }
        out = await hook.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        self.assertEqual(out["choices"][0]["message"]["content"], response["choices"][0]["message"]["content"])
        self.assertEqual(out["choices"][0]["message"]["tool_calls"], [])

    async def test_passthrough_for_streaming(self):
        hook = QwenToolcallPostHook(
            guardrail_name="qwen-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "main",
            "stream": True,
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "<tool_call>\n{\"value\":\"hello\"}\n</tool_call>",
                        "tool_calls": [],
                    },
                }
            ]
        }
        out = await hook.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        self.assertEqual(out["choices"][0]["message"]["content"], response["choices"][0]["message"]["content"])

    async def test_passthrough_for_extra_prose(self):
        hook = QwenToolcallPostHook(
            guardrail_name="qwen-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "main",
            "stream": False,
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "before\n<tool_call>\n{\"value\":\"hello\"}\n</tool_call>",
                        "tool_calls": [],
                    },
                }
            ]
        }
        out = await hook.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        self.assertEqual(out["choices"][0]["message"]["content"], response["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
