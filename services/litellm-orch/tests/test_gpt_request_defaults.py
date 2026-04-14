import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/litellm-orch/config/gpt_request_defaults.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


gpt_request_defaults = _load_module(MODULE_PATH, "gpt_request_defaults")
GPTRequestDefaults = gpt_request_defaults.GPTRequestDefaults


class TestGPTRequestDefaults(unittest.IsolatedAsyncioTestCase):
    async def test_injects_reasoning_effort_for_gpt_target_models(self):
        guardrail = GPTRequestDefaults(
            guardrail_name="gpt-request-defaults",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "deep",
            "messages": [{"role": "user", "content": "Ping"}],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertEqual(out["reasoning_effort"], "low")

    async def test_preserves_explicit_reasoning_effort(self):
        guardrail = GPTRequestDefaults(
            guardrail_name="gpt-request-defaults",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "fast",
            "reasoning_effort": "medium",
            "messages": [{"role": "user", "content": "Ping"}],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertEqual(out["reasoning_effort"], "medium")

    async def test_passthrough_for_non_target_models(self):
        guardrail = GPTRequestDefaults(
            guardrail_name="gpt-request-defaults",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "main",
            "messages": [{"role": "user", "content": "Ping"}],
        }
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="acompletion",
        )
        self.assertNotIn("reasoning_effort", out)
