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
        if isinstance(content, list):
            self.choices = [_FakeChoice(item) for item in content]
        else:
            self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(completion_tokens)


class _FakeCompletions:
    def __init__(self):
        self.verifier_calls = 0
        self.synthesis_attempts = 0
        self.candidate_markers: list[str] = []
        self.critique_calls = 0
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        prompt = kwargs["messages"][1]["content"]
        model = kwargs["model"]
        stage = "other"
        if prompt.startswith("Summarize this task"):
            stage = "triage"
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            return _FakeResponse("requirements: complete task; constraints: keep scope")
        if "Produce one candidate implementation plan" in prompt:
            stage = "candidate"
            count = kwargs.get("n", 1)
            marker_prefix = "fast" if model == "fast" else "main"
            values = [f"candidate-plan-{marker_prefix}-{idx + 1}" for idx in range(count)]
            self.candidate_markers.extend(values)
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort"), "n": count}
            )
            return _FakeResponse(values)
        if prompt.startswith("Evaluate candidates"):
            stage = "critique"
            self.critique_calls += 1
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            return _FakeResponse("TOP: 2,1\nRationale: candidate 2 is strongest.")
        if prompt.startswith("Produce the final response"):
            stage = "synthesis"
            self.synthesis_attempts += 1
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            if model == "deep" and self.synthesis_attempts == 1:
                return _FakeResponse("")
            return _FakeResponse("final-response-v1")
        if prompt.startswith("Check whether the final response"):
            stage = "verify"
            self.verifier_calls += 1
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            if self.verifier_calls == 1:
                return _FakeResponse("REPAIR: add rollback detail")
            return _FakeResponse("PASS: constraints satisfied")
        if prompt.startswith("Given the verifier feedback"):
            stage = "repair-instructions"
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            return _FakeResponse("Add explicit rollback section")
        if prompt.startswith("Revise the response"):
            stage = "rewrite"
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            return _FakeResponse("final-response-v2 with rollback")
        self.calls.append({"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")})
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


class _FakeCompletionsRejectReasoning:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        prompt = kwargs["messages"][1]["content"]
        model = kwargs["model"]
        stage = "other"
        if prompt.startswith("Summarize this task"):
            stage = "triage"
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            return _FakeResponse("requirements: complete task; constraints: keep scope")
        if "Produce one candidate implementation plan" in prompt:
            stage = "candidate"
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort"), "n": kwargs.get("n", 1)}
            )
            count = kwargs.get("n", 1)
            return _FakeResponse(["candidate-plan"] * count)
        if prompt.startswith("Produce the final response"):
            stage = "synthesis"
            effort = kwargs.get("reasoning_effort")
            self.calls.append({"stage": stage, "model": model, "reasoning_effort": effort})
            if effort:
                raise RuntimeError("unknown parameter: reasoning_effort")
            return _FakeResponse("final-response-v1")
        if prompt.startswith("Check whether the final response"):
            stage = "verify"
            self.calls.append(
                {"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")}
            )
            return _FakeResponse("PASS: constraints satisfied")
        self.calls.append({"stage": stage, "model": model, "reasoning_effort": kwargs.get("reasoning_effort")})
        return _FakeResponse("fallback")


class _FakeClientRejectReasoning:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _FakeCompletionsRejectReasoning()})()


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

    def test_extract_texts_reads_multiple_choices(self):
        response = _FakeResponse(["one", "two", "three"])
        self.assertEqual(plansearchtrio_plugin._extract_texts(response), ["one", "two", "three"])

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
        self.assertEqual(client.chat.completions.candidate_markers, ["candidate-plan-fast-1", "candidate-plan-main-1"])

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

    def test_generate_candidates_uses_n_per_model(self):
        client = _FakeClient()
        candidates, token_total = plansearchtrio_plugin._generate_candidates(
            client=client,
            request_config={},
            system_prompt="sys",
            query="q",
            triage="t",
            fast_model="fast",
            main_model="main",
            deep_model="deep",
            candidate_budget=64,
            c_fast=2,
            c_main=1,
            debug=False,
        )
        self.assertEqual(
            candidates,
            ["candidate-plan-fast-1", "candidate-plan-fast-2", "candidate-plan-main-1"],
        )
        self.assertEqual(token_total, 20)
        candidate_calls = [c for c in client.chat.completions.calls if c["stage"] == "candidate"]
        self.assertEqual(candidate_calls[0]["model"], "fast")
        self.assertEqual(candidate_calls[0]["n"], 2)
        self.assertEqual(candidate_calls[1]["model"], "main")
        self.assertEqual(candidate_calls[1]["n"], 1)

    def test_parse_top_indices_prefers_ranked_candidates(self):
        self.assertEqual(
            plansearchtrio_plugin._parse_top_indices("TOP: 2,1,2,9", candidate_count=3, k_keep=2),
            [1, 0],
        )
        self.assertEqual(
            plansearchtrio_plugin._parse_top_indices("bad", candidate_count=3, k_keep=2),
            [],
        )

    def test_internal_model_rejection_blocks_optillm_prefixes(self):
        with self.assertRaises(ValueError):
            plansearchtrio_plugin._validate_internal_model("plansearch-deep")
        with self.assertRaises(ValueError):
            plansearchtrio_plugin._validate_internal_model("moa-main")
        plansearchtrio_plugin._validate_internal_model("deep")

    def test_build_call_config_allowlist_excludes_response_format(self):
        payload = plansearchtrio_plugin._build_call_config(
            {
                "temperature": 0.2,
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.3,
                "response_format": {"type": "json_schema"},
            },
            max_tokens=256,
        )
        self.assertEqual(payload["max_tokens"], 256)
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["temperature"], 0.2)
        self.assertNotIn("response_format", payload)

    def test_synthesis_and_rewrite_use_high_reasoning_effort_on_deep_only(self):
        client = _FakeClient()
        content, _ = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="build a migration plan",
            client=client,
            model="deep",
            request_config={"plansearchtrio_mode": "full", "plansearchtrio_stage_retries": 0},
        )
        self.assertIn("rollback", content)
        synthesis_calls = [c for c in client.chat.completions.calls if c["stage"] == "synthesis"]
        rewrite_calls = [c for c in client.chat.completions.calls if c["stage"] == "rewrite"]
        self.assertGreaterEqual(len(synthesis_calls), 2)  # deep then main fallback
        self.assertGreaterEqual(len(rewrite_calls), 1)
        deep_synthesis = [c for c in synthesis_calls if c["model"] == "deep"]
        main_synthesis = [c for c in synthesis_calls if c["model"] == "main"]
        self.assertTrue(deep_synthesis)
        self.assertTrue(main_synthesis)
        self.assertTrue(all(c["reasoning_effort"] == "high" for c in deep_synthesis))
        self.assertTrue(all(c["reasoning_effort"] is None for c in main_synthesis))
        self.assertTrue(all(c["reasoning_effort"] == "high" for c in rewrite_calls if c["model"] == "deep"))
        early_stage_calls = [
            c for c in client.chat.completions.calls if c["stage"] in {"triage", "candidate", "critique", "verify"}
        ]
        self.assertTrue(all(c["reasoning_effort"] is None for c in early_stage_calls))

    def test_run_uses_critique_top_selection(self):
        client = _FakeClient()
        content, _ = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="build a migration plan",
            client=client,
            model="deep",
            request_config={"plansearchtrio_mode": "full", "plansearchtrio_stage_retries": 0},
        )
        self.assertTrue(content)
        synthesis_prompt = next(
            call for call in client.chat.completions.calls if call["stage"] == "synthesis" and call["model"] == "deep"
        )
        self.assertEqual(synthesis_prompt["reasoning_effort"], "high")


if __name__ == "__main__":
    unittest.main()
