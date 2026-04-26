import importlib.util
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "llmster_ensure_server",
    str(Path(__file__).resolve().parents[4] / "platform/ops/scripts/llmster_ensure_server.py"),
)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class LlmsterEnsureServerTests(unittest.TestCase):
    def test_parse_load_spec(self):
        spec = mod.parse_load_spec(
            "gpt-oss-20b|llmster-gpt-oss-20b-mxfp4-gguf|32768|4|512|true|4|true"
        )
        self.assertEqual(spec.model, "gpt-oss-20b")
        self.assertEqual(spec.identifier, "llmster-gpt-oss-20b-mxfp4-gguf")
        self.assertEqual(spec.context_length, 32768)
        self.assertEqual(spec.parallel, 4)
        self.assertEqual(spec.eval_batch_size, 512)
        self.assertTrue(spec.flash_attention)
        self.assertEqual(spec.num_experts, 4)
        self.assertTrue(spec.offload_kv_cache_to_gpu)

    def test_parse_load_spec_rejects_invalid_shape(self):
        with self.assertRaises(ValueError):
            mod.parse_load_spec("bad-spec")

    def test_identifier_present_checks_models_body(self):
        body = {"data": [{"id": "llmster-gpt-oss-20b-mxfp4-gguf"}, {"id": "other"}]}
        self.assertTrue(mod.identifier_present(body, "llmster-gpt-oss-20b-mxfp4-gguf"))
        self.assertFalse(mod.identifier_present(body, "missing"))

    def test_load_config_matches_expected_native_config(self):
        instance = {
            "id": "llmster-gpt-oss-20b-mxfp4-gguf",
            "config": {
                "context_length": 32768,
                "parallel": 4,
                "eval_batch_size": 512,
                "flash_attention": True,
                "num_experts": 4,
                "offload_kv_cache_to_gpu": True,
            },
        }
        spec = mod.parse_load_spec(
            "gpt-oss-20b|llmster-gpt-oss-20b-mxfp4-gguf|32768|4|512|true|4|true"
        )
        self.assertTrue(mod.load_config_matches(instance, spec))
        self.assertFalse(
            mod.load_config_matches(
                {"id": "x", "config": {**instance["config"], "flash_attention": False}},
                spec,
            )
        )


if __name__ == "__main__":
    unittest.main()
