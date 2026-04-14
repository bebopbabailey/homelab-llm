import importlib.util
import pathlib
import unittest

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
    def __init__(self, short_synthesis=None, reject_batched_models=None):
        self.short_synthesis = short_synthesis
        self.reject_batched_models = set(reject_batched_models or [])
        self.calls = []
        self.verifier_calls = 0
        self.critique_calls = 0
        self.synthesis_attempts = 0
        self.single_candidate_counts = {}

    def _record(self, stage, prompt, kwargs, raised=None):
        self.calls.append(
            {
                "stage": stage,
                "model": kwargs["model"],
                "reasoning_effort": kwargs.get("reasoning_effort"),
                "max_tokens": kwargs.get("max_tokens"),
                "n": kwargs.get("n"),
                "has_n": "n" in kwargs,
                "prompt": prompt,
                "raised": raised,
            }
        )

    def create(self, **kwargs):
        prompt = kwargs["messages"][1]["content"]
        model = kwargs["model"]

        if prompt.startswith("Summarize this task"):
            self._record("triage", prompt, kwargs)
            return _FakeResponse("requirements: complete task; constraints: keep scope")

        if "Produce one candidate implementation plan" in prompt:
            if model in self.reject_batched_models and kwargs.get("n", 1) > 1:
                self._record("candidate", prompt, kwargs, raised="batched_reject")
                raise RuntimeError("provider rejected n")
            self._record("candidate", prompt, kwargs)
            count = kwargs.get("n", 1)
            prefix = "fast" if model == "fast" else "main"
            if "n" in kwargs and count > 1:
                values = [f"candidate-plan-{prefix}-{idx + 1}" for idx in range(count)]
                return _FakeResponse(values)
            next_index = self.single_candidate_counts.get(model, 0) + 1
            self.single_candidate_counts[model] = next_index
            return _FakeResponse(f"candidate-plan-{prefix}-seq-{next_index}")

        if prompt.startswith("Evaluate candidates"):
            self.critique_calls += 1
            self._record("critique", prompt, kwargs)
            return _FakeResponse("TOP: 2,1\nRationale: candidate 2 is strongest.")

        if prompt.startswith("Produce the final response"):
            self.synthesis_attempts += 1
            self._record("synthesis", prompt, kwargs)
            if self.short_synthesis is not None and model == "deep":
                return _FakeResponse(self.short_synthesis)
            if model == "deep" and self.synthesis_attempts == 1:
                return _FakeResponse("")
            return _FakeResponse("final-response-v1")

        if prompt.startswith("Check whether the final response"):
            self.verifier_calls += 1
            self._record("verify", prompt, kwargs)
            if self.verifier_calls == 1:
                return _FakeResponse("REPAIR: add rollback detail")
            return _FakeResponse("PASS: constraints satisfied")

        if prompt.startswith("Given the verifier feedback"):
            self._record("repair-instructions", prompt, kwargs)
            return _FakeResponse("Add explicit rollback section")

        if prompt.startswith("Revise the response"):
            self._record("rewrite", prompt, kwargs)
            return _FakeResponse("final-response-v2 with rollback")

        self._record("other", prompt, kwargs)
        return _FakeResponse("fallback")


class _FakeClient:
    def __init__(self, short_synthesis=None, reject_batched_models=None):
        self.chat = type(
            "Chat",
            (),
            {"completions": _FakeCompletions(short_synthesis, reject_batched_models)},
        )()


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
        self.assertEqual((fast, main, deep), ("fast-custom", "main-custom", "deep-custom"))

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

    def test_internal_model_rejection_blocks_optillm_prefixes(self):
        with self.assertRaises(ValueError):
            plansearchtrio_plugin._validate_internal_model("plansearch-deep")
        with self.assertRaises(ValueError):
            plansearchtrio_plugin._validate_internal_model("moa-main")
        plansearchtrio_plugin._validate_internal_model("deep")

    def test_run_executes_repair_loop_and_returns_tokens(self):
        client = _FakeClient()
        content, completion_tokens = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="build a migration plan",
            client=client,
            model="deep",
            request_config={
                "plansearchtrio_mode": "full",
                "plansearchtrio_candidates_fast": 2,
                "plansearchtrio_candidates_main": 1,
                "plansearchtrio_repair_rounds": 1,
                "plansearchtrio_stage_retries": 0,
                "plansearchtrio_fallback_on_empty": True,
                "plansearchtrio_enable_repair": True,
            },
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

    def test_outer_max_tokens_no_longer_starves_internal_compact_stages(self):
        client = _FakeClient()
        content, _ = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="Draft a rollback-first deployment plan in 5 bullets.",
            client=client,
            model="deep",
            request_config={
                "plansearchtrio_mode": "auto",
                "plansearchtrio_stage_retries": 0,
                "plansearchtrio_enable_verify": False,
                "max_tokens": 32,
            },
        )
        self.assertTrue(content)
        triage_call = next(call for call in client.chat.completions.calls if call["stage"] == "triage")
        candidate_calls = [call for call in client.chat.completions.calls if call["stage"] == "candidate"]
        synthesis_call = next(call for call in client.chat.completions.calls if call["stage"] == "synthesis")
        self.assertEqual(triage_call["max_tokens"], 96)
        self.assertEqual(candidate_calls[0]["max_tokens"], 128)
        self.assertEqual(candidate_calls[1]["max_tokens"], 128)
        self.assertEqual(synthesis_call["max_tokens"], 32)

    def test_compact_mode_accepts_seven_char_synthesis_output(self):
        client = _FakeClient(short_synthesis="trio-ok")
        content, _ = plansearchtrio_plugin.run(
            system_prompt="system",
            initial_query="Reply exactly: trio-ok",
            client=client,
            model="deep",
            request_config={
                "plansearchtrio_mode": "auto",
                "plansearchtrio_stage_retries": 0,
                "plansearchtrio_enable_verify": False,
                "max_tokens": 32,
            },
        )
        self.assertEqual(content, "trio-ok")

    def test_generate_candidates_omits_n_when_count_is_one(self):
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
            c_fast=1,
            c_main=1,
            debug=False,
        )
        self.assertEqual(candidates, ["candidate-plan-fast-seq-1", "candidate-plan-main-seq-1"])
        self.assertEqual(token_total, 20)
        candidate_calls = [c for c in client.chat.completions.calls if c["stage"] == "candidate"]
        self.assertTrue(all(call["has_n"] is False for call in candidate_calls))

    def test_generate_candidates_falls_back_to_sequential_when_batched_n_is_rejected(self):
        client = _FakeClient(reject_batched_models={"fast"})
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
            c_main=0,
            debug=False,
        )
        self.assertEqual(candidates, ["candidate-plan-fast-seq-1", "candidate-plan-fast-seq-2"])
        self.assertEqual(token_total, 20)
        candidate_calls = [c for c in client.chat.completions.calls if c["stage"] == "candidate"]
        self.assertTrue(candidate_calls[0]["has_n"])
        self.assertEqual(candidate_calls[0]["n"], 2)
        self.assertEqual(candidate_calls[0]["raised"], "batched_reject")
        self.assertFalse(candidate_calls[1]["has_n"])
        self.assertFalse(candidate_calls[2]["has_n"])

    def test_parse_top_indices_prefers_ranked_candidates(self):
        self.assertEqual(
            plansearchtrio_plugin._parse_top_indices("TOP: 2,1,2,9", candidate_count=3, k_keep=2),
            [1, 0],
        )
        self.assertEqual(plansearchtrio_plugin._parse_top_indices("bad", candidate_count=3, k_keep=2), [])

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
        deep_synthesis = [c for c in synthesis_calls if c["model"] == "deep"]
        main_synthesis = [c for c in synthesis_calls if c["model"] == "main"]
        self.assertTrue(deep_synthesis)
        self.assertTrue(main_synthesis)
        self.assertTrue(all(c["reasoning_effort"] == "high" for c in deep_synthesis))
        self.assertTrue(all(c["reasoning_effort"] is None for c in main_synthesis))
        self.assertTrue(all(c["reasoning_effort"] == "high" for c in rewrite_calls if c["model"] == "deep"))

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
        )["prompt"]
        self.assertIn("Candidate 1:\ncandidate-plan-fast-2", synthesis_prompt)
        self.assertIn("Candidate 2:\ncandidate-plan-fast-1", synthesis_prompt)


if __name__ == "__main__":
    unittest.main()
