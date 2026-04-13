#!/usr/bin/env python3
"""Unit tests for viability decision logic."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "run_viability_gate.py"
)

spec = importlib.util.spec_from_file_location("run_viability_gate", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class DecisionTests(unittest.TestCase):
    def test_required_failure_is_no_go(self) -> None:
        decision, _reasons = module.decide_final_status(
            model_statuses={
                "main": "fail",
                "gpt-oss-20b": "pass",
                "gpt-oss-120b": "pass",
            },
            required_models=["main", "gpt-oss-20b"],
        )
        self.assertEqual(decision, module.DECISION_NO_GO)

    def test_required_unverified_is_unverified(self) -> None:
        decision, _reasons = module.decide_final_status(
            model_statuses={
                "main": "unverified",
                "gpt-oss-20b": "pass",
                "gpt-oss-120b": "pass",
            },
            required_models=["main", "gpt-oss-20b"],
        )
        self.assertEqual(decision, module.DECISION_UNVERIFIED)

    def test_optional_problem_is_conditional_go(self) -> None:
        decision, _reasons = module.decide_final_status(
            model_statuses={
                "main": "pass",
                "gpt-oss-20b": "pass",
                "gpt-oss-120b": "unverified",
            },
            required_models=["main", "gpt-oss-20b"],
        )
        self.assertEqual(decision, module.DECISION_CONDITIONAL_GO)

    def test_all_pass_is_go(self) -> None:
        decision, _reasons = module.decide_final_status(
            model_statuses={
                "main": "pass",
                "gpt-oss-20b": "pass",
                "gpt-oss-120b": "pass",
            },
            required_models=["main", "gpt-oss-20b"],
        )
        self.assertEqual(decision, module.DECISION_GO)


class AggregationTests(unittest.TestCase):
    def test_unreachable_smoke_is_unverified(self) -> None:
        status = module.aggregate_model_status(
            smoke={
                "functional_status": "unverified",
                "functional_pass": False,
                "behavior_changed": False,
            },
            bench_evals=[{"status": "unverified"}],
        )
        self.assertEqual(status["status"], "unverified")

    def test_no_benchmark_success_is_unverified(self) -> None:
        eval_result = module.evaluate_bench_result(
            {
                "summary": {
                    "modes": {
                        "default": {
                            "requests": 2,
                            "success": 0,
                            "failure": 2,
                            "latency_seconds": {"p50": 0, "p95": 0},
                            "metadata_rate": 0.0,
                        },
                        "entropy": {
                            "requests": 2,
                            "success": 0,
                            "failure": 2,
                            "latency_seconds": {"p50": 0, "p95": 0},
                            "metadata_rate": 0.0,
                        },
                    }
                }
            },
            module.Thresholds(
                p50_overhead_pct=25.0,
                p95_overhead_pct=35.0,
                error_delta_pct=1.0,
                entropy_metadata_rate_min=0.95,
                min_throughput_delta_pct=-15.0,
                max_error_rate_pct=0.5,
            ),
        )
        self.assertEqual(eval_result["status"], "unverified")


class ConfigAndQualityTests(unittest.TestCase):
    def test_missing_patch_path_is_unverified(self) -> None:
        payload = module.maybe_check_patch_rebase(Path("/tmp/does-not-exist.patch"))
        self.assertEqual(payload["status"], "unverified")

    def test_optional_quality_report_absent_is_skipped(self) -> None:
        payload = module.evaluate_quality_gate(None, required=False)
        self.assertEqual(payload["status"], "skipped")

    def test_required_quality_report_absent_is_unverified(self) -> None:
        payload = module.evaluate_quality_gate(None, required=True)
        self.assertEqual(payload["status"], "unverified")

    def test_gate_profile_can_resolve_models_and_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "gate.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "viability_gate": {
                            "models": ["main", "gpt-oss-20b"],
                            "required_models": ["main"],
                            "concurrency_values": [1, 2],
                            "thresholds": {
                                "p50_overhead_pct": 11.0,
                                "p95_overhead_pct": 21.0,
                                "error_delta_pct": 0.5,
                                "entropy_metadata_rate_min": 0.9,
                            },
                            "quality": {"required": True},
                        }
                    }
                )
            )
            profile, base = module._resolve_gate_profile(str(cfg_path))
            args = module.argparse.Namespace(
                gate_config=str(cfg_path),
                url=None,
                models=None,
                required_models=None,
                concurrency_values=None,
                prompts=None,
                repeats=None,
                max_tokens=None,
                smoke_timeout=None,
                bench_timeout=None,
                bearer=None,
                output_dir=None,
                check_upstream_patch=False,
                patch_path=None,
                quality_report=None,
                quality_required=False,
                p50_overhead_pct=None,
                p95_overhead_pct=None,
                error_delta_pct=None,
                entropy_metadata_rate_min=None,
                min_throughput_delta_pct=None,
                max_error_rate_pct=None,
            )
            effective = module._resolve_effective_inputs(args, profile, base)
            self.assertEqual(effective["models"], ["main", "gpt-oss-20b"])
            self.assertEqual(effective["required_models"], ["main"])
            self.assertEqual(effective["concurrency_values"], [1, 2])
            self.assertTrue(effective["quality_required"])
            self.assertEqual(effective["thresholds"].p50_overhead_pct, 11.0)
            self.assertEqual(effective["thresholds"].min_throughput_delta_pct, -15.0)

    def test_bench_eval_fails_when_throughput_drop_too_large(self) -> None:
        eval_result = module.evaluate_bench_result(
            {
                "summary": {
                    "modes": {
                        "default": {
                            "requests": 10,
                            "success": 10,
                            "failure": 0,
                            "latency_seconds": {"p50": 1.0, "p95": 2.0},
                            "metadata_rate": 0.0,
                            "completion_tokens_per_second": 100.0,
                        },
                        "entropy": {
                            "requests": 10,
                            "success": 10,
                            "failure": 0,
                            "latency_seconds": {"p50": 1.05, "p95": 2.1},
                            "metadata_rate": 1.0,
                            "completion_tokens_per_second": 70.0,
                        },
                    }
                }
            },
            module.Thresholds(
                p50_overhead_pct=25.0,
                p95_overhead_pct=35.0,
                error_delta_pct=1.0,
                entropy_metadata_rate_min=0.95,
                min_throughput_delta_pct=-15.0,
                max_error_rate_pct=0.5,
            ),
        )
        self.assertEqual(eval_result["status"], "fail")

    def test_bench_eval_fails_when_entropy_error_rate_exceeds_limit(self) -> None:
        eval_result = module.evaluate_bench_result(
            {
                "summary": {
                    "modes": {
                        "default": {
                            "requests": 10,
                            "success": 10,
                            "failure": 0,
                            "latency_seconds": {"p50": 1.0, "p95": 2.0},
                            "metadata_rate": 0.0,
                            "completion_tokens_per_second": 100.0,
                        },
                        "entropy": {
                            "requests": 10,
                            "success": 9,
                            "failure": 1,
                            "latency_seconds": {"p50": 1.05, "p95": 2.1},
                            "metadata_rate": 1.0,
                            "completion_tokens_per_second": 90.0,
                        },
                    }
                }
            },
            module.Thresholds(
                p50_overhead_pct=25.0,
                p95_overhead_pct=35.0,
                error_delta_pct=10.0,
                entropy_metadata_rate_min=0.95,
                min_throughput_delta_pct=-15.0,
                max_error_rate_pct=0.5,
            ),
        )
        self.assertEqual(eval_result["status"], "fail")


if __name__ == "__main__":
    unittest.main()
