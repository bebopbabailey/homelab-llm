import unittest
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


transcribe_utils = _load_module(
    REPO_ROOT / "layer-gateway/litellm-orch/config/transcribe_utils.py",
    "transcribe_utils",
)
strip_wrappers = transcribe_utils.strip_wrappers
strip_punct_outside_words = transcribe_utils.strip_punct_outside_words


class TestTranscribeBaseline(unittest.TestCase):
    def test_preprocess_preserves_internal_apostrophes_and_hyphens(self):
        raw = "it's a well-known thing — right? wow!"
        stripped = strip_punct_outside_words(raw)
        self.assertIn("it's", stripped)
        self.assertIn("well-known", stripped)
        self.assertNotIn("—", stripped)
        self.assertNotIn("?", stripped)
        self.assertNotIn("!", stripped)

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

    def test_golden_output_matches_expectations(self):
        raw = (REPO_ROOT / "layer-gateway/litellm-orch/tests/fixtures_transcribe_raw.txt").read_text().strip()
        expected = (REPO_ROOT / "layer-gateway/litellm-orch/tests/fixtures_transcribe_expected.txt").read_text().strip()

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
