from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


AUDIT_SCRIPT = Path(__file__).resolve().parents[1] / "submodule_pin_audit.py"
WORKTREE_SCRIPT = Path(__file__).resolve().parents[1] / "worktree_effort.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


class SubmodulePinAuditTests(unittest.TestCase):
    def make_repo(self) -> tuple[Path, Path, Path]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        repo = root / "repo"
        child = root / "child-submodule"
        repo.mkdir()
        child.mkdir()
        self.assertEqual(run(["git", "init", "-b", "master"], repo).returncode, 0)
        self.assertEqual(run(["git", "config", "user.email", "test@example.com"], repo).returncode, 0)
        self.assertEqual(run(["git", "config", "user.name", "Test User"], repo).returncode, 0)
        self.assertEqual(run(["git", "init", "-b", "master"], child).returncode, 0)
        self.assertEqual(run(["git", "config", "user.email", "test@example.com"], child).returncode, 0)
        self.assertEqual(run(["git", "config", "user.name", "Test User"], child).returncode, 0)
        self.assertEqual(run(["git", "config", "protocol.file.allow", "always"], repo).returncode, 0)
        (repo / "README.md").write_text("# test\n", encoding="utf-8")
        (repo / "scripts").mkdir()
        (repo / "scripts" / "submodule_pin_audit.py").write_text(AUDIT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "scripts" / "worktree_effort.py").write_text(WORKTREE_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (child / "sub.txt").write_text("submodule\n", encoding="utf-8")
        self.assertEqual(run(["git", "add", "."], child).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "init"], child).returncode, 0)
        add = run(["git", "-c", "protocol.file.allow=always", "submodule", "add", str(child), "layer-gateway/example-submodule"], repo)
        self.assertEqual(add.returncode, 0, msg=add.stderr)
        self.assertEqual(run(["git", "add", "."], repo).returncode, 0)
        self.assertEqual(run(["git", "commit", "-m", "init"], repo).returncode, 0)
        return root, repo, child

    def run_audit(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run(["python3", str(AUDIT_SCRIPT), *args], cwd)

    def test_submodule_pin_audit_passes_when_remote_reachable(self) -> None:
        _, repo, _ = self.make_repo()
        result = self.run_audit(repo, "--ref", "master", "--scope", "layer-gateway/example-submodule", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overall_ok"])

    def test_submodule_pin_audit_fails_when_commit_is_local_only(self) -> None:
        _, repo, child = self.make_repo()
        self.assertEqual(run(["rm", "-rf", str(child)], repo).returncode, 0)
        result = self.run_audit(repo, "--ref", "master", "--scope", "layer-gateway/example-submodule", "--strict", "--json")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["overall_ok"])
        self.assertEqual(payload["failures"][0]["path"], "layer-gateway/example-submodule")
        self.assertFalse(payload["failures"][0]["remote_commit_reachable"])


if __name__ == "__main__":
    unittest.main()
