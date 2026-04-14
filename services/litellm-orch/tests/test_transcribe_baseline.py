import asyncio
import unittest
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


transcribe_utils = _load_module(
    REPO_ROOT / "services/litellm-orch/config/transcribe_utils.py",
    "transcribe_utils",
)
sys.modules["config.transcribe_utils"] = transcribe_utils
transcribe_guardrail = _load_module(
    REPO_ROOT / "services/litellm-orch/config/transcribe_guardrail.py",
    "transcribe_guardrail",
)
strip_wrappers = transcribe_utils.strip_wrappers
strip_punct_outside_words = transcribe_utils.strip_punct_outside_words


class TestTranscribeBaseline(unittest.TestCase):
    def test_pre_call_task_transcribe_renders_provider_model_and_defaults(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe",
                    "messages": [{"role": "user", "content": "um i i think this should probably work maybe yes"}],
                    "prompt_variables": {},
                },
                "chat.completions",
            )
        )

        self.assertEqual(result["model"], "openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct")
        self.assertFalse(result["stream"])
        self.assertEqual(result["temperature"], 0.05)
        self.assertEqual(result["max_tokens"], 4096)
        self.assertNotIn("prompt_variables", result)
        self.assertEqual(result["messages"][-1]["content"], "Transcript:\num i i think this should probably work maybe yes")

    def test_pre_call_task_transcribe_vivid_accepts_optional_prompt_variables(self):
        guardrail = transcribe_guardrail.TranscribeGuardrail("transcribe-pre", "pre_call", True)
        result = asyncio.run(
            guardrail.async_pre_call_hook(
                None,
                None,
                {
                    "model": "task-transcribe-vivid",
                    "messages": [{"role": "user", "content": "uh okay this is kind of sudden but it matters a lot actually"}],
                    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
                },
                "chat.completions",
            )
        )

        self.assertEqual(result["model"], "openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct")
        self.assertFalse(result["stream"])
        self.assertEqual(result["temperature"], 0.4)
        self.assertEqual(result["frequency_penalty"], 0.2)
        self.assertNotIn("prompt_variables", result)
        self.assertEqual(
            result["messages"][-1]["content"],
            "Transcript:\nuh okay this is kind of sudden but it matters a lot actually",
        )

    def test_preprocess_preserves_internal_apostrophes_and_hyphens(self):
        raw = "it's a well-known thing — right? wow!"
        stripped = strip_punct_outside_words(raw)
        self.assertIn("it's", stripped)
        self.assertIn("well-known", stripped)
        self.assertNotIn("—", stripped)
        self.assertNotIn("?", stripped)
        self.assertNotIn("!", stripped)

    def test_preprocess_preserves_curly_apostrophes_without_normalizing(self):
        raw = "it’s still a well-known thing — right?"
        stripped = strip_punct_outside_words(raw)
        self.assertIn("it’s", stripped)
        self.assertIn("well-known", stripped)
        self.assertNotIn("—", stripped)

    def test_postfilter_strips_wrappers(self):
        cases = [
            "**Cleaned Transcript**: Hello there.",
            "# Cleaned Transcript: Hello there.",
            "Cleaned Transcript: Hello there.",
        ]
        for output in cases:
            cleaned = strip_wrappers(output)
            self.assertEqual(cleaned, "Hello there.")

    def test_postfilter_keeps_real_content(self):
        output = "Cleaned transcript is hard."
        cleaned = strip_wrappers(output)
        self.assertEqual(cleaned, output)

    def test_postfilter_strips_quoted_wrapper(self):
        output = "\"Cleaned Transcript: quoted.\""
        cleaned = strip_wrappers(output)
        self.assertEqual(cleaned, "quoted.")

    def test_guardrail_uses_shared_helpers(self):
        self.assertIs(transcribe_guardrail._strip_wrappers, strip_wrappers)
        self.assertIs(transcribe_guardrail._preprocess_transcript, strip_punct_outside_words)

    def test_golden_output_matches_expectations(self):
        raw = (REPO_ROOT / "services/litellm-orch/tests/fixtures_transcribe_raw.txt").read_text().strip()
        expected = (REPO_ROOT / "services/litellm-orch/tests/fixtures_transcribe_expected.txt").read_text().strip()

        # 1) no headings/labels
        lowered = expected.lower()
        self.assertFalse(lowered.startswith("cleaned transcript"))
        self.assertFalse(lowered.startswith("here is the cleaned transcript"))

        # 2) begins with transcript content (not empty)
        self.assertTrue(len(expected) > 0)

        # 3) no additional words introduced beyond allowed disfluency removal
        def norm_tokens(text: str) -> list[str]:
            text = strip_wrappers(text)
            text = strip_punct_outside_words(text.lower())
            tokens = text.split()
            filler = {"um", "uh", "er", "ah", "hmm", "mm", "like"}
            filtered = []
            last = None
            for tok in tokens:
                if tok in filler:
                    continue
                if tok == last:
                    continue
                filtered.append(tok)
                last = tok
            return filtered

        raw_tokens = norm_tokens(raw)
        expected_tokens = norm_tokens(expected)
        self.assertTrue(set(expected_tokens).issubset(set(raw_tokens)))

        # 4) punctuation improved (should contain sentence-ending punctuation)
        self.assertRegex(expected, r"[.!?]")


if __name__ == "__main__":
    unittest.main()
