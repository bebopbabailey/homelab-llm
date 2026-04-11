from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


START_SCRIPT = Path(__file__).resolve().parents[1] / "start_effort.py"
WORKTREE_SCRIPT = Path(__file__).resolve().parents[1] / "worktree_effort.py"
SERVICE_REGISTRY_SCRIPT = Path(__file__).resolve().parents[1] / "service_registry.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


class StartEffortTests(unittest.TestCase):
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
        (repo / "scripts" / "worktree_effort.py").write_text(WORKTREE_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "scripts" / "submodule_pin_audit.py").write_text(
            (START_SCRIPT.parents[0] / "submodule_pin_audit.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (repo / "scripts" / "service_registry.py").write_text(
            SERVICE_REGISTRY_SCRIPT.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (repo / "scripts" / "start_effort.py").write_text(START_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "platform" / "registry").mkdir(parents=True)
        (repo / "platform" / "registry" / "services.jsonl").write_text(
            json.dumps(
                {
                    "service_id": "docs-service",
                    "path": "docs",
                    "planned_path": "services/docs-service",
                    "parent_service_id": None,
                    "maturity": "supported",
                    "runtime_mode": "docs-only",
                    "service_kind": "tool",
                    "host_targets": ["local"],
                    "exposure": "internal",
                    "taxonomy_tags": ["docs"],
                    "upstream_service_ids": [],
                    "legacy_paths": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(run(["git", "add", "."], repo).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "init"], repo).returncode, 0)
        return root, repo

    def run_start(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run(["python3", str(START_SCRIPT), *args], cwd)

    def add_worktree(self, root: Path, repo: Path, name: str) -> Path:
        other = root / name
        result = run(["git", "worktree", "add", "-b", name, str(other)], repo)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return other

    def add_submodule(self, root: Path, repo: Path, rel_path: str) -> None:
        child = root / "child-submodule"
        child.mkdir()
        self.assertEqual(run(["git", "init", "-b", "master"], child).returncode, 0)
        self.assertEqual(run(["git", "config", "user.email", "test@example.com"], child).returncode, 0)
        self.assertEqual(run(["git", "config", "user.name", "Test User"], child).returncode, 0)
        self.assertEqual(run(["git", "config", "protocol.file.allow", "always"], repo).returncode, 0)
        (child / "sub.txt").write_text("submodule\n", encoding="utf-8")
        self.assertEqual(run(["git", "add", "."], child).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "init"], child).returncode, 0)
        result = run(
            ["git", "-c", "protocol.file.allow=always", "submodule", "add", str(child), rel_path],
            repo,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(run(["git", "commit", "-am", "add submodule"], repo).returncode, 0)

    def test_start_effort_creates_linked_worktree_and_registers_effort(self) -> None:
        _, repo = self.make_repo()
        result = self.run_start(repo, "--id", "demo", "--scope", "docs", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overall_ok"])
        worktree_path = Path(payload["worktree_path"])
        self.assertTrue(worktree_path.is_dir())
        status = run(["python3", str(WORKTREE_SCRIPT), "status", "--json"], worktree_path)
        status_payload = json.loads(status.stdout)
        self.assertEqual(status_payload["current_effort"]["effort_id"], "demo")
        self.assertFalse(status_payload["is_primary_worktree"])

    def test_start_effort_resolves_service_scope(self) -> None:
        _, repo = self.make_repo()
        result = self.run_start(repo, "--id", "demo-service", "--service", "docs-service", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["service_ids"], ["docs-service"])
        self.assertEqual(payload["scope_paths"], ["docs"])

    def test_start_effort_fails_from_linked_worktree(self) -> None:
        root, repo = self.make_repo()
        other = self.add_worktree(root, repo, "feature-a")
        result = self.run_start(other, "--id", "demo", "--scope", "docs", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be run from the primary worktree", result.stderr)

    def test_start_effort_fails_when_primary_is_dirty(self) -> None:
        _, repo = self.make_repo()
        (repo / "README.md").write_text("dirty\n", encoding="utf-8")
        result = self.run_start(repo, "--id", "demo", "--scope", "docs", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("primary worktree must be clean", result.stderr)

    def test_start_effort_fails_when_primary_has_local_effort_metadata(self) -> None:
        _, repo = self.make_repo()
        effort_file = repo / ".git" / "codex-effort.json"
        effort_file.write_text(
            json.dumps(
                {
                    "effort_id": "parked:repo",
                    "owner": "codex",
                    "stage": "parked",
                    "scope_paths": [],
                    "status": "active",
                    "created_at": "2026-04-09T00:00:00Z",
                    "updated_at": "2026-04-09T00:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = self.run_start(repo, "--id", "demo", "--scope", "docs", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not have local effort metadata", result.stderr)

    def test_start_effort_fails_when_branch_exists(self) -> None:
        _, repo = self.make_repo()
        self.assertEqual(run(["git", "branch", "codex/demo"], repo).returncode, 0)
        result = self.run_start(repo, "--id", "demo", "--scope", "docs", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target branch already exists", result.stderr)

    def test_start_effort_fails_when_target_path_exists(self) -> None:
        root, repo = self.make_repo()
        existing = root / "existing-worktree"
        existing.mkdir()
        result = self.run_start(repo, "--id", "demo", "--scope", "docs", "--path", str(existing), "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target worktree path already exists", result.stderr)

    def test_start_effort_initializes_overlapping_submodule_only(self) -> None:
        root, repo = self.make_repo()
        self.add_submodule(root, repo, "layer-gateway/example-submodule")
        result = self.run_start(repo, "--id", "demo", "--scope", "layer-gateway/example-submodule", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["initialized_submodules"], ["layer-gateway/example-submodule"])
        submodule_file = Path(payload["worktree_path"]) / "layer-gateway" / "example-submodule" / "sub.txt"
        self.assertTrue(submodule_file.is_file())

    def test_start_effort_rejects_broad_parallel_docs_lane(self) -> None:
        root, repo = self.make_repo()
        first = self.add_worktree(root, repo, "feature-a")
        result = run(
            ["python3", str(WORKTREE_SCRIPT), "register", "--effort-id", "feature-a", "--stage", "build", "--scope", "README.md", "--json"],
            first,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        blocked = self.run_start(repo, "--id", "docs-pass", "--scope", "docs", "--json")
        self.assertNotEqual(blocked.returncode, 0)
        payload = json.loads(blocked.stdout)
        self.assertIn("broad parallel docs/layer scopes", payload["message"])
        self.assertFalse((root / "repo-docs-pass").exists())

    def test_start_effort_cleans_up_failed_submodule_bootstrap(self) -> None:
        root, repo = self.make_repo()
        self.add_submodule(root, repo, "layer-gateway/example-submodule")
        child = root / "child-submodule"
        result = run(["rm", "-rf", str(child)], repo)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        target = root / "repo-demo"
        failed = self.run_start(repo, "--id", "demo", "--scope", "layer-gateway/example-submodule", "--path", str(target), "--json")
        self.assertNotEqual(failed.returncode, 0)
        payload = json.loads(failed.stdout)
        self.assertTrue(payload["cleanup_attempted"])
        self.assertTrue(payload["cleanup_ok"])
        self.assertFalse(target.exists())
        self.assertNotEqual(run(["git", "show-ref", "--verify", "--quiet", "refs/heads/codex/demo"], repo).returncode, 0)


if __name__ == "__main__":
    unittest.main()
