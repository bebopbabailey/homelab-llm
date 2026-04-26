import importlib.util
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/litellm-orch/config/llmster_toolcall_guardrail.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


llmster_toolcall_guardrail = _load_module(MODULE_PATH, "llmster_toolcall_guardrail")
LlmsterToolcallGuardrail = llmster_toolcall_guardrail.LlmsterToolcallGuardrail
_build_tool_calls = llmster_toolcall_guardrail._build_tool_calls
_extract_protocol_tool_call = llmster_toolcall_guardrail._extract_protocol_tool_call


class TestLlmsterToolcallHelpers(unittest.TestCase):
    def test_extracts_protocol_tool_call_with_message_payload(self):
        text = (
            "Thoughts...</thinking to=functions.open_terminal_mcp_ro_list_files"
            "<|channel|>commentary<|message|>{\"directory\":\"/home/user\"}"
        )
        out = _extract_protocol_tool_call(text)
        self.assertEqual(out, ("open_terminal_mcp_ro_list_files", '{"directory":"/home/user"}'))

    def test_build_tool_calls_maps_underscore_name_to_declared_hyphen_name(self):
        out = _build_tool_calls(
            "open_terminal_mcp_ro_list_files",
            '{"directory":"/home/user"}',
            {"openterminalmcprolistfiles": "open-terminal-mcp-ro_list_files"},
        )
        self.assertEqual(out[0]["function"]["name"], "open-terminal-mcp-ro_list_files")
        self.assertEqual(json.loads(out[0]["function"]["arguments"]), {"directory": "/home/user"})


class TestLlmsterToolcallGuardrail(unittest.IsolatedAsyncioTestCase):
    async def test_pre_call_forces_nonstream_for_tool_auto_requests(self):
        guardrail = LlmsterToolcallGuardrail(
            guardrail_name="llmster-toolcall-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "deep",
            "stream": True,
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertFalse(out["stream"])

    async def test_pre_call_passthrough_without_tools(self):
        guardrail = LlmsterToolcallGuardrail(
            guardrail_name="llmster-toolcall-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {"model": "fast", "stream": True, "messages": [{"role": "user", "content": "Ping"}]}
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertTrue(out["stream"])

    async def test_post_call_passthrough_when_tool_calls_exist(self):
        guardrail = LlmsterToolcallGuardrail(
            guardrail_name="llmster-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "deep",
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
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
        out = await guardrail.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        self.assertEqual(out["choices"][0]["message"]["tool_calls"][0]["function"]["name"], "noop")

    async def test_post_call_normalizes_protocol_tool_call_for_deep(self):
        guardrail = LlmsterToolcallGuardrail(
            guardrail_name="llmster-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "deep",
            "tool_choice": "auto",
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "open-terminal-mcp-ro_list_files"},
                }
            ],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": (
                            "Thoughts...</thinking to=functions.open_terminal_mcp_ro_list_files"
                            "<|channel|>commentary<|message|>{\"directory\":\"/home/user\"}"
                        ),
                    },
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        message = out["choices"][0]["message"]
        self.assertIsNone(message["content"])
        self.assertEqual(out["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(message["tool_calls"][0]["function"]["name"], "open-terminal-mcp-ro_list_files")
        self.assertEqual(json.loads(message["tool_calls"][0]["function"]["arguments"]), {"directory": "/home/user"})

    async def test_post_call_returns_clean_error_for_undeclared_tool(self):
        guardrail = LlmsterToolcallGuardrail(
            guardrail_name="llmster-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "fast",
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": (
                            "Oops </thinking to=functions.open_terminal_mcp_ro_list_files"
                            "<|channel|>commentary<|message|>{\"directory\":\"/home/user\"}"
                        ),
                    },
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        message = out["choices"][0]["message"]
        self.assertEqual(
            message["content"],
            "The model returned a malformed tool call for this request. Please retry the request.",
        )
        self.assertEqual(message["tool_calls"], [])
        self.assertEqual(out["choices"][0]["finish_reason"], "stop")

    async def test_post_call_returns_clean_error_for_bad_json_payload(self):
        guardrail = LlmsterToolcallGuardrail(
            guardrail_name="llmster-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "code-reasoning",
            "tool_choice": "auto",
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "open-terminal-mcp-ro_list_files"},
                }
            ],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": (
                            "Oops </thinking to=functions.open_terminal_mcp_ro_list_files"
                            "<|channel|>commentary<|message|>{\"directory\":"
                        ),
                    },
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        message = out["choices"][0]["message"]
        self.assertEqual(
            message["content"],
            "The model returned a malformed tool call for this request. Please retry the request.",
        )
        self.assertEqual(message["tool_calls"], [])
        self.assertEqual(out["choices"][0]["finish_reason"], "stop")

    async def test_post_call_passthrough_for_non_target_model(self):
        guardrail = LlmsterToolcallGuardrail(
            guardrail_name="llmster-toolcall-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "task-transcribe",
            "tool_choice": "auto",
            "tools": [{"type": "function", "function": {"name": "noop"}}],
        }
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": (
                            "Oops </thinking to=functions.noop"
                            "<|channel|>commentary<|message|>{\"value\":\"x\"}"
                        ),
                    },
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(data=data, user_api_key_dict=None, response=response)
        self.assertEqual(out["choices"][0]["message"]["content"], response["choices"][0]["message"]["content"])
