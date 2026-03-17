import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "mlxctl"
LOADER = importlib.machinery.SourceFileLoader("mlxctl_module_profiles", str(MODULE_PATH))
SPEC = importlib.util.spec_from_loader("mlxctl_module_profiles", LOADER)
mlxctl = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mlxctl)


class RuntimeProfileMetadataTests(unittest.TestCase):
    def test_runtime_profiles_file_loads_and_has_schema_version(self):
        payload = mlxctl._load_runtime_profiles()
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("profiles", payload)
        self.assertIn("glm47", payload["profiles"])
        self.assertIn("seed_oss", payload["profiles"])
        self.assertIn("gpt_oss_fast_openai_tools", payload["profiles"])
        self.assertIn("gpt_oss_tools_experimental", payload["profiles"])

    def test_profile_resolution_fails_when_explicit_profile_missing(self):
        entry = {"model_id": "mlx-custom-model", "vllm": {"profile": "nope"}}
        with self.assertRaises(SystemExit):
            mlxctl._resolve_runtime_profile(entry)

    def test_profile_resolution_uses_explicit_profile_when_present(self):
        entry = {"model_id": "mlx-custom-model", "vllm": {"profile": "generic"}}
        name, profile = mlxctl._resolve_runtime_profile(entry)
        self.assertEqual(name, "generic")
        self.assertEqual(profile["tool_choice_mode"], "none")

    def test_seed_profile_resolves_from_seed_model_id(self):
        entry = {"model_id": "mlx-seed-oss-36b-4bit-instruct"}
        name, profile = mlxctl._resolve_runtime_profile(entry)
        self.assertEqual(name, "seed_oss")
        self.assertEqual(profile["tool_call_parser"], "seed_oss")
        self.assertEqual(profile["readiness_acceptance_predicate"], "noop_tool_call")
        self.assertTrue(profile["trust_remote_code"])
        self.assertEqual(profile["chat_template_strategy"], "local_required")

    def test_gpt_oss_default_profile_has_chat_template_kwargs_and_longer_readiness(self):
        entry = {"model_id": "mlx-gpt-oss-20b-mxfp4-q4"}
        name, profile = mlxctl._resolve_runtime_profile(entry)
        self.assertEqual(name, "gpt_oss_lane")
        self.assertEqual(profile["chat_template_kwargs"]["enable_thinking"], False)
        self.assertEqual(profile["chat_template_kwargs"]["reasoning_effort"], "low")
        self.assertEqual(profile["readiness_max_tokens"], 256)

    def test_gpt_oss_tools_experimental_profile_matches_spec(self):
        payload = mlxctl._load_runtime_profiles()
        profile = payload["profiles"]["gpt_oss_tools_experimental"]
        self.assertEqual(profile["tool_choice_mode"], "auto")
        self.assertEqual(profile["tool_call_parser"], "openai")
        self.assertIsNone(profile["reasoning_parser"])
        self.assertEqual(profile["chat_template_kwargs"]["enable_thinking"], False)
        self.assertEqual(profile["chat_template_kwargs"]["reasoning_effort"], "low")
        self.assertEqual(profile["readiness_probe_mode"], "chat_tool_noop")
        self.assertEqual(profile["readiness_acceptance_predicate"], "noop_tool_call")
        self.assertEqual(profile["readiness_max_tokens"], 256)

    def test_runtime_profiles_validation_rejects_missing_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text('{"schema_version":1,"profiles":{"generic":{"tool_choice_mode":"none","auto_tool_choice_policy":"allowed","reasoning_parser_policy":"optional","readiness_probe_mode":"chat_basic","readiness_acceptance_predicate":"assistant_text_or_tool_calls","readiness_max_tokens":32}}}')
            with mock.patch.object(mlxctl, "_runtime_profiles_path", return_value=path):
                with self.assertRaises(SystemExit):
                    mlxctl._load_runtime_profiles()

    def test_vllm_render_validate_fails_when_profile_resolution_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_profile": "generic",
                        "profiles": {
                            "generic": {
                                "tool_choice_mode": "none",
                                "tool_call_parser": None,
                                "reasoning_parser": None,
                                "chat_template_mode": "tokenizer",
                                "auto_tool_choice_policy": "allowed",
                                "reasoning_parser_policy": "optional",
                                "readiness_probe_mode": "chat_basic",
                                "readiness_acceptance_predicate": "assistant_text_or_tool_calls",
                                "readiness_max_tokens": 32
                            },
                            "p1": {
                                "match_any": ["llama"],
                                "tool_choice_mode": "auto",
                                "tool_call_parser": "llama3_json",
                                "reasoning_parser": None,
                                "chat_template_mode": "tokenizer",
                                "auto_tool_choice_policy": "allowed",
                                "reasoning_parser_policy": "forbidden",
                                "readiness_probe_mode": "chat_basic",
                                "readiness_acceptance_predicate": "assistant_text_or_tool_calls",
                                "readiness_max_tokens": 32
                            },
                            "p2": {
                                "match_any": ["llama"],
                                "tool_choice_mode": "auto",
                                "tool_call_parser": "llama3_json",
                                "reasoning_parser": None,
                                "chat_template_mode": "tokenizer",
                                "auto_tool_choice_policy": "allowed",
                                "reasoning_parser_policy": "forbidden",
                                "readiness_probe_mode": "chat_basic",
                                "readiness_acceptance_predicate": "assistant_text_or_tool_calls",
                                "readiness_max_tokens": 32
                            }
                        }
                    }
                )
            )
            with mock.patch.object(mlxctl, "_runtime_profiles_path", return_value=path):
                with self.assertRaises(SystemExit):
                    mlxctl._resolve_runtime_profile({"model_id": "mlx-llama-3-3-70b-4bit-instruct"})


if __name__ == "__main__":
    unittest.main()
