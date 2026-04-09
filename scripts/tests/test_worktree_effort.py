from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "worktree_effort.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


class WorktreeEffortTests(unittest.TestCase):
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
        self.assertEqual(run(["git", "add", "."], repo).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "init"], repo).returncode, 0)
        return root, repo

    def run_script(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run(["python3", str(SCRIPT), *args], cwd)

    def add_worktree(self, root: Path, repo: Path, name: str) -> Path:
        other = root / name
        result = run(["git", "worktree", "add", "-b", name, str(other)], repo)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return other

    def test_register_status_and_close(self) -> None:
        _, repo = self.make_repo()
        other = self.add_worktree(Path(repo).parent, repo, "feature-a")
        result = self.run_script(other, "register", "--effort-id", "effort-a", "--stage", "build", "--scope", "README.md", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        status = self.run_script(other, "status", "--json")
        payload = json.loads(status.stdout)
        self.assertEqual(payload["current_effort"]["effort_id"], "effort-a")
        closed = self.run_script(other, "close", "--json")
        self.assertEqual(closed.returncode, 0, msg=closed.stderr)
        payload = json.loads(closed.stdout)
        self.assertTrue(payload["removed"])
        self.assertEqual(payload["removed_effort"]["effort_id"], "effort-a")
        status = self.run_script(other, "status", "--json")
        payload = json.loads(status.stdout)
        self.assertIsNone(payload["current_effort"])

    def test_park_creates_active_context_metadata(self) -> None:
        _, repo = self.make_repo()
        result = self.run_script(repo, "park", "--notes", "holding context", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["effort"]["stage"], "parked")
        self.assertEqual(payload["effort"]["scope_paths"], [])
        self.assertTrue(payload["effort"]["effort_id"].startswith("parked:"))
        status = self.run_script(repo, "status", "--json")
        status_payload = json.loads(status.stdout)
        self.assertEqual(status_payload["current_effort"]["stage"], "parked")
        self.assertEqual(status_payload["parked_worktrees"], [str(repo)])

    def test_build_preflight_passes_with_in_scope_dirty_file(self) -> None:
        root, repo = self.make_repo()
        other = self.add_worktree(root, repo, "feature-in-scope")
        self.run_script(other, "register", "--effort-id", "effort-a", "--stage", "build", "--scope", "docs", "--json")
        (other / "docs" / "a.md").write_text("dirty\n", encoding="utf-8")
        result = self.run_script(other, "preflight", "--stage", "build", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overall_ok"])

    def test_build_preflight_fails_for_out_of_scope_dirty_file(self) -> None:
        root, repo = self.make_repo()
        other = self.add_worktree(root, repo, "feature-out-of-scope")
        self.run_script(other, "register", "--effort-id", "effort-a", "--stage", "build", "--scope", "docs", "--json")
        (other / "README.md").write_text("dirty\n", encoding="utf-8")
        result = self.run_script(other, "preflight", "--stage", "build", "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["out_of_scope_dirty_paths"], ["README.md"])

    def test_overlap_across_active_worktrees_fails_preflight(self) -> None:
        root, repo = self.make_repo()
        left = self.add_worktree(root, repo, "feature-a")
        other = self.add_worktree(root, repo, "feature-b")
        self.run_script(left, "register", "--effort-id", "effort-a", "--stage", "build", "--scope", "docs", "--json")
        self.run_script(other, "register", "--effort-id", "effort-b", "--stage", "build", "--scope", "docs/a.md", "--json")
        result = self.run_script(left, "preflight", "--stage", "build", "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overlaps"])

    def test_discover_preflight_warns_but_does_not_fail_without_effort(self) -> None:
        _, repo = self.make_repo()
        result = self.run_script(repo, "preflight", "--stage", "discover", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("no local effort metadata registered for this worktree", payload["warnings"])

    def test_parked_dirty_worktree_does_not_block_other_build_worktree(self) -> None:
        root, repo = self.make_repo()
        other = self.add_worktree(root, repo, "feature-d")
        self.run_script(repo, "park", "--notes", "holding dirty context", "--json")
        (repo / "README.md").write_text("dirty\n", encoding="utf-8")
        self.run_script(other, "register", "--effort-id", "effort-b", "--stage", "build", "--scope", "docs", "--json")
        result = self.run_script(other, "preflight", "--stage", "build", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overall_ok"])

    def test_build_preflight_fails_when_current_worktree_is_parked(self) -> None:
        _, repo = self.make_repo()
        self.run_script(repo, "park", "--notes", "holding context", "--json")
        result = self.run_script(repo, "preflight", "--stage", "build", "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn(
            "current worktree is parked; register a build or verify effort before mutating",
            payload["blocking_issues"],
        )

    def test_duplicate_effort_id_fails_preflight(self) -> None:
        root, repo = self.make_repo()
        left = self.add_worktree(root, repo, "feature-c-left")
        other = self.add_worktree(root, repo, "feature-c")
        self.run_script(left, "register", "--effort-id", "shared", "--stage", "build", "--scope", "README.md", "--json")
        self.run_script(other, "register", "--effort-id", "shared", "--stage", "build", "--scope", "docs", "--json")
        result = self.run_script(left, "preflight", "--stage", "build", "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["duplicate_effort_ids"], ["shared"])

    def test_primary_worktree_rejects_build_registration(self) -> None:
        _, repo = self.make_repo()
        result = self.run_script(repo, "register", "--effort-id", "effort-a", "--stage", "build", "--scope", "docs", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("primary worktree is baseline-only", result.stderr)

    def test_primary_worktree_build_preflight_fails_even_with_active_metadata(self) -> None:
        _, repo = self.make_repo()
        effort_file = repo / ".git" / "codex-effort.json"
        effort_file.write_text(
            json.dumps(
                {
                    "effort_id": "effort-a",
                    "owner": "codex",
                    "stage": "build",
                    "scope_paths": ["docs"],
                    "status": "active",
                    "created_at": "2026-04-09T00:00:00Z",
                    "updated_at": "2026-04-09T00:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = self.run_script(repo, "preflight", "--stage", "build", "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn(
            "primary worktree is baseline-only; start or move this effort to a linked worktree",
            payload["blocking_issues"],
        )

    def test_status_reports_clean_primary_baseline(self) -> None:
        _, repo = self.make_repo()
        result = self.run_script(repo, "status", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["is_primary_worktree"])
        self.assertEqual(payload["primary_worktree_branch"], "master")
        self.assertTrue(payload["primary_worktree_baseline_ok"])
        self.assertEqual(payload["baseline_issues"], [])

    def test_status_reports_dirty_primary_baseline_issue(self) -> None:
        _, repo = self.make_repo()
        (repo / "README.md").write_text("dirty\n", encoding="utf-8")
        result = self.run_script(repo, "status", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["overall_ok"])
        self.assertIn("primary worktree is dirty", payload["baseline_issues"])

    def test_close_without_metadata_fails(self) -> None:
        _, repo = self.make_repo()
        result = self.run_script(repo, "close", "--json")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
