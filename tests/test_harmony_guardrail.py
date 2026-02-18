import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "layer-gateway/litellm-orch/config/harmony_guardrail.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


harmony_guardrail = _load_module(MODULE_PATH, "harmony_guardrail")
normalize_assistant_text = harmony_guardrail.normalize_assistant_text
HarmonyGuardrail = harmony_guardrail.HarmonyGuardrail
_looks_like_analysis_leak = harmony_guardrail._looks_like_analysis_leak
_safe_fallback_reply = harmony_guardrail._safe_fallback_reply


class TestHarmonyGuardrail(unittest.TestCase):
    def test_extracts_harmony_final_channel(self):
        text = (
            "<|channel|>analysis<|message|>thinking<|end|><|start|>assistant"
            "<|channel|>final<|message|>Hello from final."
        )
        normalized, changed = normalize_assistant_text(text)
        self.assertTrue(changed)
        self.assertEqual(normalized, "Hello from final.")

    def test_strips_think_blocks(self):
        text = "<think>reasoning hidden</think>\nVisible answer."
        normalized, changed = normalize_assistant_text(text)
        self.assertTrue(changed)
        self.assertEqual(normalized, "Visible answer.")

    def test_noop_for_normal_content(self):
        text = "Simple answer."
        normalized, changed = normalize_assistant_text(text)
        self.assertFalse(changed)
        self.assertEqual(normalized, text)

    def test_fallback_when_no_final_channel(self):
        text = "<|channel|>analysis<|message|>hidden<|end|><|channel|>assistant<|message|>Visible."
        normalized, changed = normalize_assistant_text(text)
        self.assertTrue(changed)
        self.assertEqual(normalized, "Visible.")

    def test_strips_raw_protocol_tokens_without_channels(self):
        text = "<|start|>assistant<|message|>Hello there<|end|>"
        normalized, changed = normalize_assistant_text(text)
        self.assertTrue(changed)
        self.assertEqual(normalized, "assistant Hello there")

    def test_detects_analysis_leak_prefix(self):
        self.assertTrue(_looks_like_analysis_leak('User says "PENG". Probably wants...'))
        self.assertFalse(_looks_like_analysis_leak("PONG"))

    def test_safe_fallback_reply(self):
        self.assertEqual(
            _safe_fallback_reply("PENG"),
            'Could you clarify what you mean by "PENG"?',
        )


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

    async def test_post_call_replaces_leaked_analysis_with_safe_reply(self):
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
                        "content": 'User says "PENG". Probably wants explanation.',
                    }
                }
            ]
        }
        out = await guardrail.async_post_call_success_hook(
            data=data,
            user_api_key_dict=None,
            response=response,
        )
        self.assertEqual(
            out["choices"][0]["message"]["content"],
            'Could you clarify what you mean by "PENG"?',
        )


if __name__ == "__main__":
    unittest.main()
