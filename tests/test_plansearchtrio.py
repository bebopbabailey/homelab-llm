import unittest
import importlib.util
import pathlib
import time

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
        self.synthesis_attempts = 0
        self.candidate_markers: list[str] = []
        self.critique_calls = 0

    def create(self, **kwargs):
        prompt = kwargs["messages"][1]["content"]
        model = kwargs["model"]
        if prompt.startswith("Summarize this task"):
            return _FakeResponse("requirements: complete task; constraints: keep scope")
        if "Candidate ID" in prompt:
            marker = prompt.split("Candidate ID:", 1)[1].strip().splitlines()[0]
            self.candidate_markers.append(marker)
            return _FakeResponse(f"candidate-plan-{marker}")
        if prompt.startswith("Evaluate candidates"):
            self.critique_calls += 1
            return _FakeResponse("top: candidate 1 then candidate 2")
        if prompt.startswith("Produce the final response"):
            self.synthesis_attempts += 1
            if model == "deep" and self.synthesis_attempts == 1:
                return _FakeResponse("")
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


class _FakeCompletionsAllEmpty:
    def create(self, **kwargs):
        return _FakeResponse("")


class _FakeClientAllEmpty:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _FakeCompletionsAllEmpty()})()


class PlanSearchTrioTests(unittest.TestCase):
    def test_int_param_clamps(self):
        cfg = {"x": "99"}
        self.assertEqual(plansearchtrio_plugin._int_param(cfg, "x", 2, 1, 8), 8)
        cfg = {"x": "bad"}
        self.assertEqual(plansearchtrio_plugin._int_param(cfg, "x", 2, 1, 8), 2)

    def test_pick_models_prefers_config(self):
        cfg = {
            "plansearchtrio_fast_model": "fast-custom",
            "plansearchtrio_main_model": "main-custom",
            "plansearchtrio_deep_model": "deep-custom",
        }
        fast, main, deep = plansearchtrio_plugin._pick_models(cfg, "deep")
        self.assertEqual(fast, "fast-custom")
        self.assertEqual(main, "main-custom")
        self.assertEqual(deep, "deep-custom")

    def test_extract_text_handles_structured_content(self):
        class _Msg:
            def __init__(self):
                self.content = [
                    {"type": "output_text", "text": "hello"},
                    {"type": "output_text", "text": " world"},
                ]

        class _Choice:
            def __init__(self):
                self.message = _Msg()

        class _Resp:
            def __init__(self):
                self.choices = [_Choice()]
                self.usage = _FakeUsage()

        self.assertEqual(plansearchtrio_plugin._extract_text(_Resp()), "hello world")

    def test_run_executes_repair_loop_and_returns_tokens(self):
        client = _FakeClient()
        cfg = {
            "plansearchtrio_mode": "full",
            "plansearchtrio_candidates_fast": 2,
            "plansearchtrio_candidates_main": 1,
            "plansearchtrio_repair_rounds": 1,
            "plansearchtrio_max_workers": 2,
            "plansearchtrio_stage_retries": 0,
            "plansearchtrio_fallback_on_empty": True,
            "plansearchtrio_enable_repair": True,
        }
        content, completion_tokens = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="build a migration plan",
            client=client,
            model="deep",
            request_config=cfg,
        )
        self.assertIn("rollback", content)
        self.assertGreater(completion_tokens, 0)

    def test_run_uses_fallback_without_error_prefix_when_all_stages_empty(self):
        client = _FakeClientAllEmpty()
        content, completion_tokens = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="build a migration plan",
            client=client,
            model="deep",
            request_config={
                "plansearchtrio_stage_retries": 1,
                "plansearchtrio_fallback_on_empty": True,
            },
        )
        self.assertTrue(content)
        self.assertFalse(content.startswith("PLANSEARCHTRIO_ERROR:"))
        self.assertGreaterEqual(completion_tokens, 0)

    def test_auto_mode_uses_compact_candidate_counts(self):
        client = _FakeClient()
        content, _ = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="build a migration plan",
            client=client,
            model="deep",
            request_config={"plansearchtrio_mode": "auto", "plansearchtrio_stage_retries": 0},
        )
        self.assertTrue(content)
        self.assertEqual(len(client.chat.completions.candidate_markers), 2)

    def test_latency_budget_skips_critique(self):
        client = _FakeClient()
        original_within_budget = plansearchtrio_plugin._within_budget
        plansearchtrio_plugin._within_budget = lambda *_args, **_kwargs: False
        try:
            content, _ = plansearchtrio_plugin.run(
                system_prompt="system",
                initial_query="build a migration plan",
                client=client,
                model="deep",
                request_config={
                    "plansearchtrio_mode": "full",
                    "plansearchtrio_latency_budget_ms": 1,
                    "plansearchtrio_enable_critique": True,
                    "plansearchtrio_stage_retries": 0,
                },
            )
        finally:
            plansearchtrio_plugin._within_budget = original_within_budget
        self.assertTrue(content)
        self.assertEqual(client.chat.completions.critique_calls, 0)

    def test_parallel_candidates_preserve_job_order(self):
        original = plansearchtrio_plugin._chat_resilient

        def _fake_chat_resilient(*args, **kwargs):
            stage = kwargs.get("stage_name")
            if stage is None and len(args) >= 7:
                stage = args[6]
            if stage == "candidate-0":
                time.sleep(0.02)
            return f"text-{stage}", 1

        plansearchtrio_plugin._chat_resilient = _fake_chat_resilient
        try:
            candidates, token_total = plansearchtrio_plugin._parallel_candidates(
                client=object(),
                request_config={},
                system_prompt="sys",
                query="q",
                triage="t",
                fast_model="fast",
                main_model="main",
                candidate_budget=64,
                c_fast=2,
                c_main=1,
                max_workers=3,
                retries=0,
                min_chars=1,
                debug=False,
            )
        finally:
            plansearchtrio_plugin._chat_resilient = original

        self.assertEqual(
            candidates,
            ["text-candidate-0", "text-candidate-1", "text-candidate-2"],
        )
        self.assertEqual(token_total, 3)


if __name__ == "__main__":
    unittest.main()
