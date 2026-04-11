from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


CLOSEOUT_SCRIPT = Path(__file__).resolve().parents[1] / "closeout_effort.py"
START_SCRIPT = Path(__file__).resolve().parents[1] / "start_effort.py"
WORKTREE_SCRIPT = Path(__file__).resolve().parents[1] / "worktree_effort.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


class CloseoutEffortTests(unittest.TestCase):
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
        (repo / "docs").mkdir()
        (repo / "docs" / "a.md").write_text("a\n", encoding="utf-8")
        (repo / "scripts").mkdir()
        (repo / "scripts" / "start_effort.py").write_text(START_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "scripts" / "worktree_effort.py").write_text(WORKTREE_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "scripts" / "closeout_effort.py").write_text(CLOSEOUT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "scripts" / "repo_hygiene_audit.py").write_text(
            "import json\nprint(json.dumps({'overall_ok': True}))\n",
            encoding="utf-8",
        )
        (repo / "scripts" / "control_plane_sync_audit.py").write_text(
            "import json\nprint(json.dumps({'overall_ok': True}))\n",
            encoding="utf-8",
        )
        self.assertEqual(run(["git", "add", "."], repo).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "init"], repo).returncode, 0)
        return root, repo

    def run_start(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run(["python3", str(START_SCRIPT), *args], cwd)

    def run_closeout(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run(["python3", str(CLOSEOUT_SCRIPT), *args], cwd)

    def test_closeout_commits_merges_and_cleans_lane(self) -> None:
        root, repo = self.make_repo()
        result = self.run_start(repo, "--id", "demo", "--scope", "docs", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        worktree = Path(payload["worktree_path"])
        (worktree / "docs" / "a.md").write_text("updated\n", encoding="utf-8")
        closed = self.run_closeout(repo, "--worktree", str(worktree), "--message", "docs: closeout demo", "--json")
        self.assertEqual(closed.returncode, 0, msg=closed.stderr)
        closed_payload = json.loads(closed.stdout)
        self.assertTrue(closed_payload["merged_to_master"])
        self.assertTrue(closed_payload["worktree_removed"])
        self.assertTrue(closed_payload["branch_deleted"])
        self.assertFalse(worktree.exists())
        self.assertIn("updated", (repo / "docs" / "a.md").read_text(encoding="utf-8"))

    def test_closeout_fails_when_nothing_to_close_out(self) -> None:
        root, repo = self.make_repo()
        result = self.run_start(repo, "--id", "demo", "--scope", "docs", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        worktree = Path(payload["worktree_path"])
        run(["python3", str(WORKTREE_SCRIPT), "close", "--json"], worktree)
        failed = self.run_closeout(repo, "--worktree", str(worktree), "--json")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("nothing to close out", failed.stderr)


if __name__ == "__main__":
    unittest.main()
