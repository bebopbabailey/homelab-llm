from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "repo_hygiene_audit.py"


MANIFEST_TEMPLATE = {
    "allowed_root_files": [
        ".gitignore",
        "AGENTS.md",
        "DOCS_CONTRACT.md",
        "README.md",
        "NOW.md",
        "opencode.json",
    ],
    "journal": {
        "entry_regex": r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$",
        "non_entry_files": ["README.md", "index.md"],
    },
    "archive": {
        "top_level_rollup_regex": r"^\d{4}-\d{2}-[a-z0-9][a-z0-9-]*\.md$",
        "allowed_top_level_files": ["README.md"],
        "legacy_subdir": "legacy",
    },
}


class RepoHygieneAuditTests(unittest.TestCase):
    def make_repo(
        self,
        *,
        extra_root_files: list[str] | None = None,
        journal_entries: list[str] | None = None,
        index_lines: list[str] | None = None,
        archive_files: list[str] | None = None,
        malformed_manifest: bool = False,
    ) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        repo = Path(tempdir.name)
        (repo / "docs" / "_core").mkdir(parents=True)
        (repo / "docs" / "journal").mkdir(parents=True)
        (repo / "docs" / "archive" / "legacy").mkdir(parents=True)

        if malformed_manifest:
            (repo / "docs" / "_core" / "root_hygiene_manifest.json").write_text("[]", encoding="utf-8")
        else:
            (repo / "docs" / "_core" / "root_hygiene_manifest.json").write_text(
                json.dumps(MANIFEST_TEMPLATE, indent=2) + "\n",
                encoding="utf-8",
            )

        for name in [".gitignore", "AGENTS.md", "DOCS_CONTRACT.md", "README.md", "NOW.md", "opencode.json"]:
            (repo / name).write_text(f"{name}\n", encoding="utf-8")
        for name in extra_root_files or []:
            (repo / name).write_text(f"{name}\n", encoding="utf-8")

        entries = journal_entries or []
        for name in entries:
            (repo / "docs" / "journal" / name).write_text(f"# {name}\n", encoding="utf-8")
        (repo / "docs" / "journal" / "README.md").write_text("# README\n", encoding="utf-8")
        index = ["# Journal Index"]
        index.extend(index_lines or [])
        (repo / "docs" / "journal" / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")

        (repo / "docs" / "archive" / "README.md").write_text("# Archive\n", encoding="utf-8")
        for name in archive_files or []:
            (repo / "docs" / "archive" / name).write_text(f"# {name}\n", encoding="utf-8")
        return repo

    def run_script(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = ["python3", str(SCRIPT), "--repo-root", str(repo), *args]
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def test_root_scope_flags_unexpected_root_file(self) -> None:
        repo = self.make_repo(extra_root_files=["junk.txt"])
        result = self.run_script(repo, "--scope", "root", "--json")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["root_ok"])
        self.assertEqual(payload["unexpected_root_files"], ["junk.txt"])

    def test_root_scope_ignores_git_worktree_file(self) -> None:
        repo = self.make_repo(extra_root_files=[".git"])
        result = self.run_script(repo, "--scope", "root", "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(payload["root_ok"])
        self.assertEqual(payload["unexpected_root_files"], [])

    def test_journal_scope_requires_real_link_targets(self) -> None:
        repo = self.make_repo(
            journal_entries=["2026-04-02-sample.md"],
            index_lines=["- `2026-04-02-sample.md`"],
        )
        result = self.run_script(repo, "--scope", "journal", "--json")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["journal_index_ok"])
        self.assertEqual(payload["journal_missing_from_index"], ["2026-04-02-sample.md"])
        self.assertEqual(payload["journal_noncanonical_index_lines"], ["- `2026-04-02-sample.md`"])

    def test_journal_readme_is_not_treated_as_entry(self) -> None:
        repo = self.make_repo(
            journal_entries=["2026-04-02-sample.md"],
            index_lines=["- [2026-04-02 sample](2026-04-02-sample.md)"],
        )
        result = self.run_script(repo, "--scope", "journal", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["journal_entries"], ["2026-04-02-sample.md"])
        self.assertEqual(payload["journal_non_entry_markdown"], [])
        self.assertTrue(payload["journal_index_ok"])

    def test_archive_scope_flags_non_rollup_top_level_file(self) -> None:
        repo = self.make_repo(archive_files=["REPORT.md"])
        result = self.run_script(repo, "--scope", "archive", "--json")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["archive_ok"])
        self.assertEqual(payload["archive_non_rollup_top_level_files"], ["REPORT.md"])

    def test_malformed_manifest_is_an_error(self) -> None:
        repo = self.make_repo(malformed_manifest=True)
        result = self.run_script(repo, "--json")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["overall_ok"])
        self.assertTrue(payload["errors"])

    def test_strict_scope_exits_non_zero(self) -> None:
        repo = self.make_repo(extra_root_files=["junk.txt"])
        result = self.run_script(repo, "--scope", "root", "--strict", "--json")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
