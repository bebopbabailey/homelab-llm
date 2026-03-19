import importlib.util
import sys
import unittest

SPEC = importlib.util.spec_from_file_location(
    "llmster_ensure_server",
    "/home/christopherbailey/homelab-llm/platform/ops/scripts/llmster_ensure_server.py",
)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class LlmsterEnsureServerTests(unittest.TestCase):
    def test_parse_load_spec(self):
        spec = mod.parse_load_spec("gpt-oss-20b|llmster-gpt-oss-20b-mxfp4-gguf|32768|4")
        self.assertEqual(spec.model, "gpt-oss-20b")
        self.assertEqual(spec.identifier, "llmster-gpt-oss-20b-mxfp4-gguf")
        self.assertEqual(spec.context_length, 32768)
        self.assertEqual(spec.parallel, 4)

    def test_parse_load_spec_rejects_invalid_shape(self):
        with self.assertRaises(ValueError):
            mod.parse_load_spec("bad-spec")


if __name__ == "__main__":
    unittest.main()
