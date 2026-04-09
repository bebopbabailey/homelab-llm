#!/usr/bin/env python3
"""Audit repo-local control-plane documentation sync.

Usage:
  uv run python scripts/control_plane_sync_audit.py
  uv run python scripts/control_plane_sync_audit.py --json
  uv run python scripts/control_plane_sync_audit.py --strict --json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_HYGIENE_REQUIRED = {
    "docs/foundation/testing.md": ["repo_hygiene_audit.py", "root_ok", "journal_index_ok", "worktree_effort.py", "start_effort.py", "primary worktree", "park", "close"],
    "docs/_core/CHANGE_RULES.md": ["repo_hygiene_audit.py", "repo-hygiene.yml", "root_hygiene_manifest.json", "worktree_effort.py", "start_effort.py", "CONCURRENT_EFFORTS.md"],
    "scripts/README.md": ["repo_hygiene_audit.py", "--scope", "--strict", "worktree_effort.py", "start_effort.py", "preflight", "park", "close"],
    "DOCS_CONTRACT.md": ["root_hygiene_manifest.json", "repo_hygiene_audit.py"],
    ".github/workflows/repo-hygiene.yml": ["repo_hygiene_audit.py", "--scope root --strict", "control_plane_sync_audit.py"],
}

SKILL_REQUIRED = {
    ".codex/skills/homelab-durability/SKILL.md": [
        "homelab-durability",
        "homelab_durability",
        "Discover",
        "Design",
        "Build",
        "Verify",
        "Before proposing commands or file edits",
        "Rollback is required",
        "Rollback is not required",
        "worktree_effort.py",
        "primary worktree",
        "baseline-only",
        "start_effort.py",
        "park",
    ],
    "docs/OPENCODE.md": [
        "homelab-durability",
        "homelab_durability",
        "Discover",
        "Design",
        "Build",
        "Verify",
        "startup declaration",
        "rollback",
        "worktree_effort.py",
        "primary worktree",
        "baseline-only",
        "start_effort.py",
        "separate worktree",
        "park",
    ],
    "docs/INTEGRATIONS.md": [
        "homelab-durability",
        "homelab_durability",
        "Discover",
        "Design",
        "Build",
        "Verify",
        "conditional",
        "rollback",
    ],
    "docs/_core/CONCURRENT_EFFORTS.md": [
        "One implementation effort per worktree",
        "worktree_effort.py",
        "primary worktree",
        "baseline-only",
        "start_effort.py",
        "NOW.md is project-level status",
        "park",
        "parked",
        "close",
    ],
}


def audit_contract(repo_root: Path, requirements: dict[str, list[str]]) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for rel_path, tokens in requirements.items():
        path = repo_root / rel_path
        if not path.is_file():
            missing[rel_path] = ["<missing file>"]
            continue
        text = path.read_text(encoding="utf-8")
        absent = [token for token in tokens if token not in text]
        if absent:
            missing[rel_path] = absent
    return missing


def audit_repo(repo_root: Path) -> dict[str, object]:
    repo_hygiene_missing = audit_contract(repo_root, REPO_HYGIENE_REQUIRED)
    skill_sync_missing = audit_contract(repo_root, SKILL_REQUIRED)
    errors: list[str] = []
    return {
        "repo_hygiene_sync_missing": repo_hygiene_missing,
        "repo_hygiene_sync_ok": not repo_hygiene_missing,
        "skill_sync_missing": skill_sync_missing,
        "skill_sync_ok": not skill_sync_missing,
        "errors": errors,
        "overall_ok": not repo_hygiene_missing and not skill_sync_missing and not errors,
    }


def print_table(payload: dict[str, object]) -> None:
    print("control_plane_sync")
    print(f"repo_hygiene_sync_ok: {'yes' if payload['repo_hygiene_sync_ok'] else 'no'}")
    if payload["repo_hygiene_sync_missing"]:
        print("repo_hygiene_sync_missing:")
        for path, tokens in payload["repo_hygiene_sync_missing"].items():
            print(f"- {path}: {', '.join(tokens)}")
    else:
        print("repo_hygiene_sync_missing:\n-")
    print(f"skill_sync_ok: {'yes' if payload['skill_sync_ok'] else 'no'}")
    if payload["skill_sync_missing"]:
        print("skill_sync_missing:")
        for path, tokens in payload["skill_sync_missing"].items():
            print(f"- {path}: {', '.join(tokens)}")
    else:
        print("skill_sync_missing:\n-")
    if payload["errors"]:
        print("errors:")
        for error in payload["errors"]:
            print(f"- {error}")
    print(f"overall_ok: {'yes' if payload['overall_ok'] else 'no'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Print JSON payload")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when sync gaps exist")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to the repo root to audit",
    )
    args = parser.parse_args()

    payload = audit_repo(Path(args.repo_root).resolve())
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_table(payload)
    if args.strict and not payload["overall_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
