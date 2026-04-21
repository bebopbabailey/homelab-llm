from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ABANDON_SCRIPT = Path(__file__).resolve().parents[1] / "abandon_effort.py"
WORKTREE_SCRIPT = Path(__file__).resolve().parents[1] / "worktree_effort.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


class AbandonEffortTests(unittest.TestCase):
    def make_repo(self) -> tuple[Path, Path]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        repo = root / "repo"
        repo.mkdir()
        self.assertEqual(run(["git", "init", "-b", "master"], repo).returncode, 0)
        self.assertEqual(run(["git", "config", "user.email", "test@example.com"], repo).returncode, 0)
        self.assertEqual(run(["git", "config", "user.name", "Test User"], repo).returncode, 0)
        (repo / "README.md").write_text("# test\n", encoding="utf-8")
        (repo / "docs" / "journal").mkdir(parents=True)
        (repo / "docs" / "journal" / "index.md").write_text(
            "# Journal Index\n\n- [2026-04-01-existing](2026-04-01-existing.md)\n",
            encoding="utf-8",
        )
        (repo / "docs" / "journal" / "2026-04-01-existing.md").write_text("# Existing\n", encoding="utf-8")
        (repo / "scripts").mkdir()
        (repo / "scripts" / "abandon_effort.py").write_text(ABANDON_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "scripts" / "worktree_effort.py").write_text(WORKTREE_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(run(["git", "add", "."], repo).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "init"], repo).returncode, 0)
        return root, repo

    def add_worktree(self, root: Path, repo: Path, name: str) -> Path:
        other = root / name
        result = run(["git", "worktree", "add", "-b", name, str(other)], repo)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return other

    def run_abandon(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run(["python3", str(ABANDON_SCRIPT), *args], cwd)

    def test_clean_abandon_removes_worktree_and_branch(self) -> None:
        root, repo = self.make_repo()
        worktree = self.add_worktree(root, repo, "failed-clean")
        (worktree / "README.md").write_text("# abandoned\n", encoding="utf-8")
        self.assertEqual(run(["git", "commit", "-am", "abandoned code"], worktree).returncode, 0)
        result = self.run_abandon(repo, "--worktree", str(worktree), "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["worktree_removed"])
        self.assertTrue(payload["branch_deleted"])
        self.assertFalse(worktree.exists())
        self.assertNotEqual(run(["git", "show-ref", "--verify", "--quiet", "refs/heads/failed-clean"], repo).returncode, 0)

    def test_journal_delta_blocks_without_salvage(self) -> None:
        root, repo = self.make_repo()
        worktree = self.add_worktree(root, repo, "failed-journal")
        entry = worktree / "docs" / "journal" / "2026-04-02-failed.md"
        entry.write_text("# Failed\n", encoding="utf-8")
        self.assertEqual(run(["git", "add", str(entry.relative_to(worktree))], worktree).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "journal"], worktree).returncode, 0)
        result = self.run_abandon(repo, "--worktree", str(worktree), "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["salvage_required"])
        self.assertEqual(payload["journal_deltas"]["added_entries"], ["docs/journal/2026-04-02-failed.md"])
        self.assertTrue(worktree.exists())

    def test_salvage_journal_commits_entry_updates_index_and_removes_lane(self) -> None:
        root, repo = self.make_repo()
        worktree = self.add_worktree(root, repo, "failed-salvage")
        entry = worktree / "docs" / "journal" / "2026-04-02-failed.md"
        entry.write_text("# Failed\n", encoding="utf-8")
        self.assertEqual(run(["git", "add", str(entry.relative_to(worktree))], worktree).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "journal"], worktree).returncode, 0)
        result = self.run_abandon(repo, "--worktree", str(worktree), "--salvage-journal", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["salvage_commit_sha"])
        self.assertFalse(worktree.exists())
        self.assertTrue((repo / "docs" / "journal" / "2026-04-02-failed.md").is_file())
        index = (repo / "docs" / "journal" / "index.md").read_text(encoding="utf-8")
        self.assertIn("(2026-04-02-failed.md)", index)

    def test_modified_existing_entry_becomes_new_correction_entry(self) -> None:
        root, repo = self.make_repo()
        worktree = self.add_worktree(root, repo, "failed-modified")
        existing = worktree / "docs" / "journal" / "2026-04-01-existing.md"
        existing.write_text("# Existing\n\ncorrected detail\n", encoding="utf-8")
        self.assertEqual(run(["git", "commit", "-am", "modify journal"], worktree).returncode, 0)
        result = self.run_abandon(
            repo,
            "--worktree",
            str(worktree),
            "--salvage-journal",
            "--salvage-entry",
            "2026-04-03-abandoned-branch-journal-salvage.md",
            "--json",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        original = (repo / "docs" / "journal" / "2026-04-01-existing.md").read_text(encoding="utf-8")
        self.assertEqual(original, "# Existing\n")
        correction = (repo / "docs" / "journal" / "2026-04-03-abandoned-branch-journal-salvage.md").read_text(encoding="utf-8")
        self.assertIn("corrected detail", correction)
        self.assertIn("2026-04-01-existing.md", correction)

    def test_deleted_journal_entry_is_reported_but_not_applied(self) -> None:
        root, repo = self.make_repo()
        worktree = self.add_worktree(root, repo, "failed-delete")
        (worktree / "docs" / "journal" / "2026-04-01-existing.md").unlink()
        self.assertEqual(run(["git", "add", "-A", "docs/journal"], worktree).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "delete journal"], worktree).returncode, 0)
        result = self.run_abandon(repo, "--worktree", str(worktree), "--salvage-journal", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["journal_deltas"]["deleted_entries"], ["docs/journal/2026-04-01-existing.md"])
        self.assertTrue((repo / "docs" / "journal" / "2026-04-01-existing.md").is_file())


if __name__ == "__main__":
    unittest.main()
