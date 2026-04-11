from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "docs_contract_audit.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


class DocsContractAuditTests(unittest.TestCase):
    def make_repo(self) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        repo = Path(tempdir.name)
        (repo / "scripts").mkdir()
        (repo / "scripts" / "docs_contract_audit.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        return repo

    def test_audit_discovers_services_and_experiments_roots(self) -> None:
        repo = self.make_repo()
        for rel in ("services/grafana", "experiments/system-monitor", "experiments/legacy/optillm-local-gateway"):
            root = repo / rel
            root.mkdir(parents=True)
            for name in ("README.md", "SERVICE_SPEC.md", "ARCHITECTURE.md", "AGENTS.md", "CONSTRAINTS.md", "RUNBOOK.md", "TASKS.md"):
                (root / name).write_text("x\n", encoding="utf-8")
        result = run(["python3", str(repo / "scripts" / "docs_contract_audit.py"), "--json"], repo)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["overall_ok"])
        self.assertEqual(
            sorted(Path(item["path"]).relative_to(repo).as_posix() for item in payload["services"]),
            ["experiments/legacy/optillm-local-gateway", "experiments/system-monitor", "services/grafana"],
        )
