from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "control_plane_sync_audit.py"


FILES = {
    ".codex/skills/homelab-durability/SKILL.md": "homelab-durability homelab_durability Discover Design Build Verify Before proposing commands or file edits Rollback is required Rollback is not required worktree_effort.py primary worktree baseline-only start_effort.py park closeout_effort.py no auto-rebase NOW.md",
    "docs/OPENCODE.md": "homelab-durability homelab_durability Discover Design Build Verify startup declaration rollback worktree_effort.py primary worktree baseline-only start_effort.py separate worktree park closeout_effort.py submodule_pin_audit.py NOW.md auto-rebase",
    "docs/INTEGRATIONS.md": "homelab-durability homelab_durability Discover Design Build Verify conditional rollback",
    "docs/foundation/testing.md": "repo_hygiene_audit.py root_ok journal_index_ok worktree_effort.py start_effort.py closeout_effort.py submodule_pin_audit.py primary worktree park close metadata-only NOW.md",
    "docs/_core/CHANGE_RULES.md": "repo_hygiene_audit.py repo-hygiene.yml root_hygiene_manifest.json worktree_effort.py start_effort.py submodule_pin_audit.py closeout_effort.py CONCURRENT_EFFORTS.md",
    "scripts/README.md": "repo_hygiene_audit.py --scope --strict worktree_effort.py start_effort.py submodule_pin_audit.py closeout_effort.py preflight park close metadata-only NOW.md auto-rebase",
    "DOCS_CONTRACT.md": "root_hygiene_manifest.json repo_hygiene_audit.py",
    ".github/workflows/repo-hygiene.yml": "repo_hygiene_audit.py --scope root --strict control_plane_sync_audit.py",
    "docs/_core/CONCURRENT_EFFORTS.md": "One implementation effort per worktree worktree_effort.py primary worktree baseline-only start_effort.py NOW.md is project-level status park parked close closeout_effort.py metadata-only broad parallel",
}


class ControlPlaneSyncAuditTests(unittest.TestCase):
    def make_repo(self, *, drop_token_from: tuple[str, str] | None = None) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        repo = Path(tempdir.name)
        for rel_path, content in FILES.items():
            path = repo / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            text = content
            if drop_token_from and rel_path == drop_token_from[0]:
                text = text.replace(drop_token_from[1], "")
            path.write_text(text + "\n", encoding="utf-8")
        return repo

    def run_script(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = ["python3", str(SCRIPT), "--repo-root", str(repo), *args]
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def test_clean_repo_is_ok(self) -> None:
        repo = self.make_repo()
        result = self.run_script(repo, "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overall_ok"])

    def test_missing_token_is_reported(self) -> None:
        repo = self.make_repo(drop_token_from=("docs/OPENCODE.md", "Build"))
        result = self.run_script(repo, "--json")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["overall_ok"])
        self.assertEqual(payload["skill_sync_missing"]["docs/OPENCODE.md"], ["Build"])

    def test_strict_mode_exits_non_zero(self) -> None:
        repo = self.make_repo(drop_token_from=("scripts/README.md", "--scope"))
        result = self.run_script(repo, "--strict", "--json")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
