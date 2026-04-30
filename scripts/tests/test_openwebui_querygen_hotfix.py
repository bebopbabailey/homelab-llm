import tempfile
import unittest
from pathlib import Path

from scripts import openwebui_querygen_hotfix as hotfix


class OpenWebuiQuerygenHotfixTests(unittest.TestCase):
    def test_infers_retrieval_target_from_middleware_target(self):
        middleware_target = Path("/tmp/site-packages/open_webui/utils/middleware.py")
        self.assertEqual(
            hotfix.infer_retrieval_target(middleware_target),
            Path("/tmp/site-packages/open_webui/routers/retrieval.py"),
        )

    def test_patch_text_upgrades_first_pass_querygen_block(self):
        original = hotfix.QUERYGEN_FIRST_PASS_BLOCK
        patched, changed, statuses = hotfix.patch_text(
            original, hotfix.PATCH_SPECS["middleware"]
        )
        self.assertTrue(changed)
        self.assertIn(hotfix.QUERYGEN_PATCH_MARKER, patched)
        self.assertEqual(statuses["querygen"], "patched")

    def test_patch_text_upgrades_retrieval_hygiene_block(self):
        original = hotfix.RESULT_HYGIENE_OLD
        patched, changed, statuses = hotfix.patch_text(
            original, hotfix.PATCH_SPECS["retrieval"]
        )
        self.assertTrue(changed)
        self.assertIn(hotfix.RESULT_HYGIENE_PATCH_MARKER, patched)
        self.assertEqual(statuses["web_search_result_hygiene"], "patched")

    def test_patch_target_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "middleware.py"
            target.write_text(hotfix.QUERYGEN_FIRST_PASS_BLOCK, encoding="utf-8")

            changed_once, statuses_once = hotfix.patch_target(
                target, hotfix.PATCH_SPECS["middleware"]
            )
            changed_twice, statuses_twice = hotfix.patch_target(
                target, hotfix.PATCH_SPECS["middleware"]
            )

            self.assertTrue(changed_once)
            self.assertFalse(changed_twice)
            self.assertEqual(statuses_once["querygen"], "patched")
            self.assertEqual(statuses_twice["querygen"], "already_patched")


if __name__ == "__main__":
    unittest.main()
