import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/litellm-orch/chatgpt5_adapter.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


chatgpt5_adapter = _load_module(MODULE_PATH, "chatgpt5_adapter")
ChatGPT5Adapter = chatgpt5_adapter.ChatGPT5Adapter
AdapterConfig = chatgpt5_adapter.AdapterConfig


class TestChatGPT5Adapter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = ChatGPT5Adapter(
            AdapterConfig(
                ccproxy_api_base="http://127.0.0.1:4010/codex/v1",
                ccproxy_auth_token="token",
                deep_api_base="http://127.0.0.1:8126/v1",
                deep_model="openai/deep",
                deep_api_key="dummy",
            )
        )

    async def test_chat_passthrough_when_ccproxy_returns_text(self):
        async def fake_chat(payload):
            return 200, {
                "id": "chatcmpl_ccproxy",
                "choices": [{"message": {"content": "codex ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            }

        async def fake_responses(payload):
            raise AssertionError("responses fallback should not run")

        async def fake_deep(payload):
            raise AssertionError("deep fallback should not run")

        self.adapter._call_ccproxy_chat = fake_chat
        self.adapter._call_ccproxy_responses = fake_responses
        self.adapter._call_deep_chat = fake_deep

        out = await self.adapter.handle_chat_completions(
            {"model": "chatgpt-5", "messages": [{"role": "user", "content": "hi"}]}
        )
        self.assertEqual(out["id"], "chatcmpl_ccproxy")

    async def test_chat_falls_back_to_deep_when_ccproxy_returns_no_text(self):
        async def fake_chat(payload):
            return 502, {"detail": "format chain failed"}

        async def fake_responses(payload):
            return 200, {"id": "resp_raw", "status": "completed"}

        async def fake_deep(payload):
            return 200, {
                "choices": [{"message": {"content": "deep ok"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            }

        self.adapter._call_ccproxy_chat = fake_chat
        self.adapter._call_ccproxy_responses = fake_responses
        self.adapter._call_deep_chat = fake_deep

        out = await self.adapter.handle_chat_completions(
            {"model": "chatgpt-5", "messages": [{"role": "user", "content": "review this diff"}]}
        )
        self.assertEqual(out["choices"][0]["message"]["content"], "deep ok")
        self.assertEqual(out["usage"]["total_tokens"], 5)

    async def test_responses_falls_back_to_deep_and_builds_output_text(self):
        async def fake_responses(payload):
            return 200, {"id": "resp_raw", "status": "completed"}

        async def fake_deep(payload):
            return 200, {
                "choices": [{"message": {"content": "deep response"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 4, "total_tokens": 6},
            }

        self.adapter._call_ccproxy_responses = fake_responses
        self.adapter._call_deep_chat = fake_deep

        out = await self.adapter.handle_responses({"model": "chatgpt-5", "input": "review this"})
        self.assertEqual(out["output_text"], "deep response")
        self.assertEqual(out["output"][0]["content"][0]["text"], "deep response")
        self.assertEqual(out["usage"]["total_tokens"], 6)


class TestAdapterHelpers(unittest.TestCase):
    def test_sanitize_drops_tool_fields(self):
        payload = chatgpt5_adapter._sanitize_payload(
            {
                "model": "chatgpt-5",
                "messages": [{"role": "user", "content": "hello"}],
                "tools": [{"type": "function", "name": "noop"}],
                "tool_choice": "auto",
                "stream": True,
            },
            endpoint="chat",
        )
        self.assertNotIn("tools", payload)
        self.assertNotIn("tool_choice", payload)
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["temperature"], 0.0)

    def test_deep_provider_model_strips_openai_prefix(self):
        adapter = ChatGPT5Adapter(
            AdapterConfig(
                ccproxy_api_base="http://127.0.0.1:4010/codex/v1",
                ccproxy_auth_token="token",
                deep_api_base="http://127.0.0.1:8126/v1",
                deep_model="openai/llmster-gpt-oss-120b-mxfp4-gguf",
                deep_api_key="dummy",
            )
        )
        self.assertEqual(adapter._deep_provider_model(), "llmster-gpt-oss-120b-mxfp4-gguf")


if __name__ == "__main__":
    unittest.main()
