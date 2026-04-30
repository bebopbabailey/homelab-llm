from __future__ import annotations

import os
import tempfile
import unittest

from app.config import _env_int, _env_secret


class ConfigHelpersTests(unittest.TestCase):
    def test_env_int_uses_default_for_missing_or_invalid(self) -> None:
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MEMORY_TEST_INT", None)
            self.assertEqual(_env_int("MEMORY_TEST_INT", 42), 42)

        with unittest.mock.patch.dict(os.environ, {"MEMORY_TEST_INT": "not-an-int"}, clear=False):
            self.assertEqual(_env_int("MEMORY_TEST_INT", 42), 42)

    def test_env_int_parses_valid_integer(self) -> None:
        with unittest.mock.patch.dict(os.environ, {"MEMORY_TEST_INT": "77"}, clear=False):
            self.assertEqual(_env_int("MEMORY_TEST_INT", 42), 77)

    def test_env_secret_prefers_inline_then_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("file-secret\n")
            path = handle.name
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))

        with unittest.mock.patch.dict(
            os.environ,
            {
                "MEMORY_TEST_SECRET": "inline-secret",
                "MEMORY_TEST_SECRET_FILE": path,
            },
            clear=False,
        ):
            self.assertEqual(
                _env_secret("MEMORY_TEST_SECRET", "MEMORY_TEST_SECRET_FILE"),
                "inline-secret",
            )

        with unittest.mock.patch.dict(
            os.environ,
            {
                "MEMORY_TEST_SECRET_FILE": path,
            },
            clear=True,
        ):
            self.assertEqual(
                _env_secret("MEMORY_TEST_SECRET", "MEMORY_TEST_SECRET_FILE"),
                "file-secret",
            )

    def test_env_secret_returns_empty_when_unset_or_missing_file(self) -> None:
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_env_secret("MEMORY_TEST_SECRET", "MEMORY_TEST_SECRET_FILE"), "")

        with unittest.mock.patch.dict(
            os.environ,
            {"MEMORY_TEST_SECRET_FILE": "/tmp/does-not-exist-memory-secret"},
            clear=True,
        ):
            self.assertEqual(_env_secret("MEMORY_TEST_SECRET", "MEMORY_TEST_SECRET_FILE"), "")


if __name__ == "__main__":
    unittest.main()
