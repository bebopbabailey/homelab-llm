import asyncio
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


task_json_guardrail = _load_module(
    REPO_ROOT / "layer-gateway/litellm-orch/config/task_json_guardrail.py",
    "task_json_guardrail",
)


class TestTaskJsonGuardrail(unittest.TestCase):
    def test_pre_call_shapes_request_for_task_json(self):
        guardrail = task_json_guardrail.TaskJsonGuardrail("task-json-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-json",
                    "stream": True,
                    "messages": [{"role": "user", "content": "call mom tomorrow, buy milk, pick up paper towels"}],
                    "tools": [{"type": "function", "function": {"name": "noop"}}],
                    "tool_choice": "auto",
                    "parallel_tool_calls": True,
                    "functions": [{"name": "noop"}],
                    "function_call": {"name": "noop"},
                },
                "chat.completions",
            )
        )

        self.assertEqual(result["model"], "openai/llmster-gpt-oss-20b-mxfp4-gguf")
        self.assertFalse(result["stream"])
        self.assertEqual(result["temperature"], 0.0)
        self.assertEqual(result["max_tokens"], 1024)
        self.assertNotIn("tools", result)
        self.assertNotIn("tool_choice", result)
        self.assertNotIn("parallel_tool_calls", result)
        self.assertNotIn("functions", result)
        self.assertNotIn("function_call", result)
        self.assertEqual(result["response_format"]["json_schema"]["name"], "task_json_payload")
        self.assertIn("Transcript:\ncall mom tomorrow, buy milk, pick up paper towels", result["messages"][-1]["content"])

    def test_post_call_normalizes_payload_and_salvages_unknown_keys(self):
        guardrail = task_json_guardrail.TaskJsonGuardrail("task-json-post", "post_call", True)
        response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "todo": ["Call Mom tomorrow", "Call Mom tomorrow"],
                                "grocery": ["milk"],
                                "purchase": ["paper towels"],
                                "other": {
                                    "items": ["Denver Friday at 4"],
                                    "attributes": {"emotion": "anxious"},
                                    "mood": "stressed",
                                },
                                "appointments": ["Denver Friday at 4"],
                                "time": "Friday 4pm",
                            }
                        )
                    }
                }
            ]
        }
        result = asyncio.run(
            guardrail.async_post_call_success_hook(
                None,
                {"model": "openai/llmster-gpt-oss-20b-mxfp4-gguf", "response_format": task_json_guardrail.TASK_JSON_SCHEMA},
                response,
            )
        )

        payload = json.loads(result["choices"][0]["message"]["content"])
        self.assertEqual(payload["todo"], ["Call Mom tomorrow"])
        self.assertEqual(payload["grocery"], ["milk"])
        self.assertEqual(payload["purchase"], ["paper towels"])
        self.assertEqual(payload["other"]["items"], ["Denver Friday at 4"])
        self.assertEqual(payload["other"]["attributes"]["emotion"], "anxious")
        self.assertEqual(payload["other"]["attributes"]["mood"], "stressed")
        self.assertEqual(payload["other"]["attributes"]["time"], "Friday 4pm")

    def test_post_call_falls_back_to_canonical_payload_after_failed_repair(self):
        guardrail = task_json_guardrail.TaskJsonGuardrail("task-json-post", "post_call", True)
        response = {"choices": [{"message": {"content": "not json at all"}}]}
        with patch.object(task_json_guardrail, "_repair_once", AsyncMock(return_value={"choices": [{"message": {"content": "still bad"}}]})):
            result = asyncio.run(
                guardrail.async_post_call_success_hook(
                    None,
                    {
                        "model": "openai/llmster-gpt-oss-20b-mxfp4-gguf",
                        "response_format": task_json_guardrail.TASK_JSON_SCHEMA,
                        "messages": [{"role": "user", "content": "call mom"}],
                        "api_base": "http://127.0.0.1:8126/v1",
                    },
                    response,
                )
            )

        payload = json.loads(result["choices"][0]["message"]["content"])
        self.assertEqual(payload["todo"], [])
        self.assertEqual(payload["grocery"], [])
        self.assertEqual(payload["purchase"], [])
        self.assertEqual(payload["other"]["items"], [])
        self.assertEqual(payload["other"]["attributes"]["guardrail_status"], "repair_failed")
