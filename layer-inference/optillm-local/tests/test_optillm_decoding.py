#!/usr/bin/env python3
"""Unit tests for OptiLLM decode-time patch helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "runtime"
    / "patches"
    / "mlx_lm"
    / "optillm_decoding.py"
)

spec = importlib.util.spec_from_file_location("optillm_decoding", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ResolveDecodingTests(unittest.TestCase):
    def test_decoding_takes_precedence_over_optillm_approach(self) -> None:
        args = module.resolve_decoding_arguments(
            {
                "decoding": "entropy_decoding",
                "optillm_approach": "moa|bon",
                "temperature": 0.5,
            },
            allow_experimental=True,
        )
        self.assertEqual(args.technique, "entropy_decoding")

    def test_optillm_approach_maps_when_decoding_missing(self) -> None:
        args = module.resolve_decoding_arguments(
            {
                "optillm_approach": "router|entropy_decoding",
                "temperature": 0.7,
            },
            allow_experimental=True,
        )
        self.assertEqual(args.technique, "entropy_decoding")

    def test_unimplemented_technique_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            module.resolve_decoding_arguments(
                {
                    "decoding": "cot_decoding",
                    "temperature": 0.6,
                },
                allow_experimental=True,
            )

    def test_decoding_params_override_top_level_entropy_values(self) -> None:
        args = module.resolve_decoding_arguments(
            {
                "decoding": "entropy_decoding",
                "temperature": 0.7,
                "entropy_target": 1.0,
                "decoding_params": {
                    "entropy_target": 2.9,
                    "entropy_alpha": 0.5,
                },
            },
            allow_experimental=True,
        )
        self.assertEqual(args.technique, "entropy_decoding")
        self.assertAlmostEqual(args.params["entropy_target"], 2.9)
        self.assertAlmostEqual(args.params["entropy_alpha"], 0.5)

    def test_decoding_params_must_be_object(self) -> None:
        with self.assertRaises(ValueError):
            module.resolve_decoding_arguments(
                {
                    "decoding": "entropy_decoding",
                    "temperature": 0.7,
                    "decoding_params": "not-an-object",
                },
                allow_experimental=True,
            )

    def test_feature_flag_required_for_non_default_decoding(self) -> None:
        with self.assertRaises(ValueError):
            module.resolve_decoding_arguments(
                {
                    "decoding": "entropy_decoding",
                    "temperature": 0.6,
                },
                allow_experimental=False,
            )


class EntropyMathTests(unittest.TestCase):
    def test_adaptive_temperature_decreases_when_entropy_is_high(self) -> None:
        high_entropy = module.compute_adaptive_temperature(
            base_temperature=0.7,
            entropy=4.0,
            target_entropy=2.6,
            alpha=0.35,
            min_temperature=0.2,
            max_temperature=1.1,
        )
        low_entropy = module.compute_adaptive_temperature(
            base_temperature=0.7,
            entropy=1.0,
            target_entropy=2.6,
            alpha=0.35,
            min_temperature=0.2,
            max_temperature=1.1,
        )
        self.assertLess(high_entropy, low_entropy)

    def test_metadata_summary_contains_expected_fields(self) -> None:
        decoding = module.DecodingArguments(
            technique="entropy_decoding",
            return_metadata=True,
            params={},
        )
        state = module.EntropyState(
            base_temperature=0.7,
            target_entropy=2.6,
            alpha=0.35,
            min_temperature=0.2,
            max_temperature=1.1,
            history_limit=8,
        )
        state.record(2.3, 0.61)
        state.record(2.9, 0.54)
        payload = module.build_decoding_metadata(decoding, state, "main")
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["technique"], "entropy_decoding")
        self.assertEqual(payload["resolved_model"], "main")
        self.assertEqual(payload["steps"], 2)
        self.assertIn("entropy_mean", payload)
        self.assertIn("temperature_min", payload)


if __name__ == "__main__":
    unittest.main()
