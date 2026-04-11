from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "service_registry_audit.py"
REGISTRY_SCRIPT = Path(__file__).resolve().parents[1] / "service_registry.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


class ServiceRegistryAuditTests(unittest.TestCase):
    def make_repo(self) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        repo = Path(tempdir.name)
        (repo / "platform" / "registry").mkdir(parents=True)
        (repo / "scripts").mkdir()
        (repo / "scripts" / "service_registry.py").write_text(REGISTRY_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / "scripts" / "service_registry_audit.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        return repo

    def test_audit_passes_when_registry_covers_service_specs(self) -> None:
        repo = self.make_repo()
        (repo / "layer-interface" / "open-webui").mkdir(parents=True)
        (repo / "layer-interface" / "open-webui" / "SERVICE_SPEC.md").write_text("spec\n", encoding="utf-8")
        (repo / "platform" / "registry" / "services.jsonl").write_text(
            json.dumps(
                {
                    "service_id": "open-webui",
                    "path": "layer-interface/open-webui",
                    "planned_path": "services/open-webui",
                    "parent_service_id": None,
                    "maturity": "supported",
                    "runtime_mode": "long-running",
                    "service_kind": "ui",
                    "host_targets": ["mini"],
                    "exposure": "lan",
                    "taxonomy_tags": ["ui"],
                    "upstream_service_ids": [],
                    "legacy_paths": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = run(["python3", str(SCRIPT), "--repo-root", str(repo), "--json"], repo)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overall_ok"])

    def test_audit_flags_missing_registry_entry(self) -> None:
        repo = self.make_repo()
        (repo / "layer-tools" / "open-terminal").mkdir(parents=True)
        (repo / "layer-tools" / "open-terminal" / "SERVICE_SPEC.md").write_text("spec\n", encoding="utf-8")
        (repo / "platform" / "registry" / "services.jsonl").write_text("", encoding="utf-8")
        result = run(["python3", str(SCRIPT), "--repo-root", str(repo), "--json"], repo)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["overall_ok"])
        self.assertEqual(payload["missing_registry_entries"], ["layer-tools/open-terminal"])


if __name__ == "__main__":
    unittest.main()
