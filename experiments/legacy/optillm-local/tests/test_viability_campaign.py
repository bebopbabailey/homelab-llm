#!/usr/bin/env python3
"""Unit tests for viability campaign aggregation logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "run_viability_campaign.py"
)

spec = importlib.util.spec_from_file_location("run_viability_campaign", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class CampaignHelperTests(unittest.TestCase):
    def test_parse_json_fragment_handles_noise_prefix(self) -> None:
        payload = module.parse_json_fragment(
            "some log line\n{\n  \"final_decision\": \"GO\",\n  \"report_path\": \"/tmp/report.json\"\n}\n"
        )
        self.assertEqual(payload["final_decision"], "GO")
        self.assertEqual(payload["report_path"], "/tmp/report.json")

    def test_parse_json_fragment_empty_returns_empty_object(self) -> None:
        self.assertEqual(module.parse_json_fragment(""), {})

    def test_decision_from_returncode_mapping(self) -> None:
        self.assertEqual(module.decision_from_returncode(0), module.DECISION_GO)
        self.assertEqual(module.decision_from_returncode(1), module.DECISION_NO_GO)
        self.assertEqual(module.decision_from_returncode(2), module.DECISION_UNVERIFIED)
        self.assertEqual(module.decision_from_returncode(3), module.DECISION_CONDITIONAL_GO)
        self.assertEqual(module.decision_from_returncode(99), module.DECISION_UNVERIFIED)

    def test_aggregate_decisions_worst_case_wins(self) -> None:
        summary = module.aggregate_decisions(
            [
                module.DECISION_GO,
                module.DECISION_CONDITIONAL_GO,
                module.DECISION_NO_GO,
            ]
        )
        self.assertEqual(summary["overall_decision"], module.DECISION_NO_GO)
        self.assertFalse(summary["stable"])
        self.assertEqual(summary["decision_counts"][module.DECISION_GO], 1)
        self.assertEqual(summary["decision_counts"][module.DECISION_CONDITIONAL_GO], 1)
        self.assertEqual(summary["decision_counts"][module.DECISION_NO_GO], 1)

    def test_aggregate_decisions_stable_when_all_same(self) -> None:
        summary = module.aggregate_decisions(
            [
                module.DECISION_UNVERIFIED,
                module.DECISION_UNVERIFIED,
            ]
        )
        self.assertTrue(summary["stable"])
        self.assertEqual(summary["overall_decision"], module.DECISION_UNVERIFIED)


if __name__ == "__main__":
    unittest.main()
