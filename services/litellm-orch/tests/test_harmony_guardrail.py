import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/litellm-orch/config/harmony_guardrail.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


harmony_guardrail = _load_module(MODULE_PATH, "harmony_guardrail")
normalize_assistant_text = harmony_guardrail.normalize_assistant_text
HarmonyGuardrail = harmony_guardrail.HarmonyGuardrail


class TestHarmonyGuardrail(unittest.TestCase):
    def test_extracts_harmony_final_channel(self):
        text = (
            "<|channel|>analysis<|message|>thinking<|end|><|start|>assistant"
            "<|channel|>final<|message|>Hello from final."
        )
        normalized, changed = normalize_assistant_text(text)
        self.assertTrue(changed)
        self.assertEqual(normalized, "Hello from final.")

    def test_noop_for_normal_content(self):
        text = "Simple answer."
        normalized, changed = normalize_assistant_text(text)
        self.assertFalse(changed)
        self.assertEqual(normalized, text)

    def test_noop_when_harmony_missing_final_channel(self):
        text = "<|channel|>analysis<|message|>hidden<|end|><|channel|>assistant<|message|>Visible."
        normalized, changed = normalize_assistant_text(text)
        self.assertFalse(changed)
        self.assertEqual(normalized, text)

    def test_strict_guard_passthrough_for_non_harmony_tokens(self):
        text = "<|start|>assistant<|message|>Hello there<|end|>"
        normalized, changed = normalize_assistant_text(text)
        self.assertFalse(changed)
        self.assertEqual(normalized, text)


class TestHarmonyPreCallGuardrail(unittest.IsolatedAsyncioTestCase):
    async def test_pre_call_sanitizes_tagged_history_message(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "deep",
            "messages": [
                {"role": "user", "content": "Ping"},
                {
                    "role": "assistant",
                    "content": "<|channel|>analysis<|message|>hidden<|end|><|channel|>final<|message|>PONG",
                    "reasoning": "abc",
                },
            ],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertEqual(out["messages"][1]["content"], "PONG")
        self.assertNotIn("reasoning", out["messages"][1])

    async def test_pre_call_only_mutates_assistant_history(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "deep",
            "messages": [
                {
                    "role": "user",
                    "content": "<|channel|>analysis<|message|>This is literal text from user.",
                },
                {"role": "assistant", "content": "No tags here."},
            ],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertEqual(out["messages"][0]["content"], data["messages"][0]["content"])
        self.assertEqual(out["messages"][1]["content"], "No tags here.")

    async def test_pre_call_preserves_stream_true_for_gpt_lanes_by_default(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "fast",
            "stream": True,
            "messages": [{"role": "user", "content": "Ping"}],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertTrue(out["stream"])
        self.assertEqual(out["reasoning_effort"], "low")

    async def test_pre_call_can_force_stream_false_when_explicitly_enabled(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-pre",
            event_hook="pre_call",
            default_on=True,
            coerce_stream_false=True,
        )
        data = {
            "model": "fast",
            "stream": True,
            "messages": [{"role": "user", "content": "Ping"}],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertFalse(out["stream"])

    async def test_pre_call_does_not_force_stream_false_for_main(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "main",
            "stream": True,
            "messages": [{"role": "user", "content": "Ping"}],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertTrue(out["stream"])
        self.assertNotIn("reasoning_effort", out)

    async def test_post_call_normalizes_harmony_for_gpt_lanes(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "fast",
            "messages": [{"role": "user", "content": "PENG"}],
        }
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "<|channel|>analysis<|message|>hidden<|end|><|channel|>final<|message|>PONG",
                    }
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(
            data=data,
            user_api_key_dict=None,
            response=response,
        )
        self.assertEqual(out["choices"][0]["message"]["content"], "PONG")

    async def test_post_call_strips_reasoning_fields_for_gpt_lanes(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "fast",
            "messages": [{"role": "user", "content": "Ping"}],
        }
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "pong",
                        "reasoning": "hidden",
                        "reasoning_content": "hidden",
                    }
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(
            data=data,
            user_api_key_dict=None,
            response=response,
        )
        self.assertEqual(out["choices"][0]["message"]["content"], "pong")
        self.assertNotIn("reasoning", out["choices"][0]["message"])
        self.assertNotIn("reasoning_content", out["choices"][0]["message"])

    async def test_post_call_passthrough_for_main_lane(self):
        guardrail = HarmonyGuardrail(
            guardrail_name="harmony-post",
            event_hook="post_call",
            default_on=True,
        )
        data = {
            "model": "main",
            "messages": [{"role": "user", "content": "PENG"}],
        }
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "<|channel|>analysis<|message|>hidden<|end|><|channel|>final<|message|>PONG",
                    }
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(
            data=data,
            user_api_key_dict=None,
            response=response,
        )
        self.assertEqual(out["choices"][0]["message"]["content"], response["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
