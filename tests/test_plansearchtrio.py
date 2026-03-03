import unittest
import importlib.util
import pathlib

try:
    from optillm.plugins import plansearchtrio_plugin  # type: ignore
except ImportError:
    plugin_path = pathlib.Path(__file__).resolve().parents[1] / "optillm" / "plugins" / "plansearchtrio_plugin.py"
    spec = importlib.util.spec_from_file_location("plansearchtrio_plugin", plugin_path)
    assert spec and spec.loader
    plansearchtrio_plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plansearchtrio_plugin)


class _FakeUsage:
    def __init__(self, completion_tokens=10):
        self.completion_tokens = completion_tokens


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content, completion_tokens=10):
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(completion_tokens)


class _FakeCompletions:
    def __init__(self):
        self.verifier_calls = 0

    def create(self, **kwargs):
        prompt = kwargs["messages"][1]["content"]
        if prompt.startswith("Summarize this task"):
            return _FakeResponse("requirements: complete task; constraints: keep scope")
        if "Candidate ID" in prompt:
            marker = prompt.split("Candidate ID:", 1)[1].strip().splitlines()[0]
            return _FakeResponse(f"candidate-plan-{marker}")
        if prompt.startswith("Evaluate candidates"):
            return _FakeResponse("top: candidate 1 then candidate 2")
        if prompt.startswith("Produce the final response"):
            return _FakeResponse("final-response-v1")
        if prompt.startswith("Check whether the final response"):
            self.verifier_calls += 1
            if self.verifier_calls == 1:
                return _FakeResponse("REPAIR: add rollback detail")
            return _FakeResponse("PASS: constraints satisfied")
        if prompt.startswith("Given the verifier feedback"):
            return _FakeResponse("Add explicit rollback section")
        if prompt.startswith("Revise the response"):
            return _FakeResponse("final-response-v2 with rollback")
        return _FakeResponse("fallback")


class _FakeClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _FakeCompletions()})()


class PlanSearchTrioTests(unittest.TestCase):
    def test_int_param_clamps(self):
        cfg = {"x": "99"}
        self.assertEqual(plansearchtrio_plugin._int_param(cfg, "x", 2, 1, 8), 8)
        cfg = {"x": "bad"}
        self.assertEqual(plansearchtrio_plugin._int_param(cfg, "x", 2, 1, 8), 2)

    def test_pick_models_prefers_config(self):
        cfg = {
            "plansearchtrio_fast_model": "openai/fast-custom",
            "plansearchtrio_main_model": "openai/main-custom",
            "plansearchtrio_deep_model": "openai/deep-custom",
        }
        fast, main, deep = plansearchtrio_plugin._pick_models(cfg, "openai/deep")
        self.assertEqual(fast, "openai/fast-custom")
        self.assertEqual(main, "openai/main-custom")
        self.assertEqual(deep, "openai/deep-custom")

    def test_run_executes_repair_loop_and_returns_tokens(self):
        client = _FakeClient()
        cfg = {
            "plansearchtrio_candidates_fast": 2,
            "plansearchtrio_candidates_main": 1,
            "plansearchtrio_repair_rounds": 1,
            "plansearchtrio_max_workers": 2,
        }
        content, completion_tokens = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="build a migration plan",
            client=client,
            model="openai/deep",
            request_config=cfg,
        )
        self.assertIn("rollback", content)
        self.assertGreater(completion_tokens, 0)


if __name__ == "__main__":
    unittest.main()
