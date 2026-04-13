from pathlib import Path
import importlib.util
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/llama-cpp-server/scripts/studio_model_retention.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


retention = _load_module(MODULE_PATH, "studio_model_retention")


class TestStudioModelRetention(unittest.TestCase):
    def test_active_main_model_is_kept_by_default_for_hf_store(self):
        entry = retention._classify(
            "/Users/thestudio/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4",
            10,
            set(),
            None,
        )
        self.assertEqual(entry.action, "keep")

    def test_explicit_delete_target_classifies_delete(self):
        entry = retention._classify(
            "/Users/thestudio/models/hf/models--mlx-community--gemma-3-27b-it-qat-4bit",
            10,
            {"qwen3-next-80b-a3b-instruct-mlx-mxfp4"},
            None,
        )
        self.assertEqual(entry.action, "delete")
        self.assertIn("explicit_delete_target", entry.reason)

    def test_active_llmster_120b_model_is_kept_by_default_for_lmstudio_store(self):
        entry = retention._classify(
            "/Users/thestudio/.lmstudio/models/lmstudio-community/gpt-oss-120b-GGUF",
            10,
            set(),
            None,
        )
        self.assertEqual(entry.action, "keep")

    def test_huggingface_cache_duplicate_does_not_inherit_keep(self):
        entry = retention._classify(
            "/Users/thestudio/.cache/huggingface/hub/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4",
            10,
            set(),
            None,
        )
        self.assertEqual(entry.action, "delete")

    def test_staged_slug_is_preserved(self):
        entry = retention._classify(
            "/Users/thestudio/Library/Caches/llama.cpp/ggml-org_gpt-oss-20b-GGUF_gpt-oss-20b-mxfp4.gguf",
            10,
            set(),
            "gpt-oss-20b-mxfp4",
        )
        self.assertEqual(entry.action, "stage")


if __name__ == "__main__":
    unittest.main()
