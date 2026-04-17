import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "qwen_agent_shadow_probe.py"
SPEC = importlib.util.spec_from_file_location("qwen_agent_shadow_probe", MODULE_PATH)
probe = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class QwenAgentShadowProbeTests(unittest.TestCase):
    def test_parse_bool_arg_accepts_true_and_false(self):
        self.assertTrue(probe.parse_bool_arg("true"))
        self.assertFalse(probe.parse_bool_arg("false"))

    def test_contains_raw_tool_markup_detects_xmlish_tokens(self):
        payload = {"arguments": '<tool_call>\n{"name":"noop"}\n</tool_call>'}
        self.assertTrue(probe.contains_raw_tool_markup(payload))

    def test_parse_json_arguments_rejects_non_object(self):
        parsed, error = probe.parse_json_arguments('["x"]')
        self.assertIsNone(parsed)
        self.assertIn("JSON object", error)

    def test_schema_validate_arguments_rejects_extra_keys(self):
        schema = {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        }
        ok, error = probe.schema_validate_arguments(schema, {"path": "main.py", "extra": "nope"})
        self.assertFalse(ok)
        self.assertIn("unexpected keys", error)

    def test_build_probe_cases_has_expected_case_names(self):
        cases = probe.build_probe_cases()
        self.assertEqual(set(cases), {"one_function", "two_function", "code_helper"})

    def test_summarize_marks_partial_when_only_some_cases_succeed(self):
        summary = probe.summarize(
            [
                {"case": "one_function", "use_raw_api": False, "attempts": 3, "successes": 3},
                {"case": "two_function", "use_raw_api": False, "attempts": 3, "successes": 0},
                {"case": "code_helper", "use_raw_api": False, "attempts": 3, "successes": 0},
            ]
        )
        self.assertEqual(summary["verdict"], "partial")


if __name__ == "__main__":
    unittest.main()
