#!/usr/bin/env python3
"""Audit repo-root, journal, and archive hygiene contracts.

Usage:
  uv run python scripts/repo_hygiene_audit.py
  uv run python scripts/repo_hygiene_audit.py --json
  uv run python scripts/repo_hygiene_audit.py --scope root --strict --json
  uv run python scripts/repo_hygiene_audit.py --scope all --strict --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


MANIFEST_PATH = Path("docs/_core/root_hygiene_manifest.json")
SCOPE_CHOICES = ("all", "root", "journal", "archive", "gitlinks")


def load_manifest(repo_root: Path) -> dict[str, object]:
    manifest_path = repo_root / MANIFEST_PATH
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"root hygiene manifest must be an object: {manifest_path}")
    if not isinstance(data.get("allowed_root_files"), list):
        raise ValueError(f"manifest missing allowed_root_files: {manifest_path}")
    journal = data.get("journal")
    archive = data.get("archive")
    if not isinstance(journal, dict) or not isinstance(archive, dict):
        raise ValueError(f"manifest missing journal/archive sections: {manifest_path}")
    return data


def scan_root_files(repo_root: Path) -> list[str]:
    ignored = {".git"}
    return sorted(path.name for path in repo_root.iterdir() if path.is_file() and path.name not in ignored)


def parse_journal_index(index_path: Path) -> tuple[set[str], list[str], list[str]]:
    if not index_path.is_file():
        return set(), [], []
    link_targets: list[str] = []
    noncanonical_lines: list[str] = []
    link_pattern = re.compile(r"\(([^)]+\.md)\)")
    for line in index_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        matches = link_pattern.findall(stripped)
        if matches:
            link_targets.extend(matches)
            if "[" not in stripped or "](" not in stripped:
                noncanonical_lines.append(stripped)
            continue
        if ".md" in stripped:
            noncanonical_lines.append(stripped)
    duplicates = sorted({name for name in link_targets if link_targets.count(name) > 1})
    return set(link_targets), noncanonical_lines, duplicates


def audit_root(repo_root: Path, manifest: dict[str, object]) -> dict[str, object]:
    allowed_root_files = sorted(str(name) for name in manifest["allowed_root_files"])
    root_files = scan_root_files(repo_root)
    unexpected_root_files = sorted(name for name in root_files if name not in allowed_root_files)
    return {
        "allowed_root_files": allowed_root_files,
        "unexpected_root_files": unexpected_root_files,
        "root_ok": not unexpected_root_files,
    }


def audit_journal(repo_root: Path, manifest: dict[str, object]) -> dict[str, object]:
    journal_cfg = manifest["journal"]
    assert isinstance(journal_cfg, dict)
    entry_regex = str(journal_cfg["entry_regex"])
    non_entry_files = set(str(name) for name in journal_cfg["non_entry_files"])
    pattern = re.compile(entry_regex)
    journal_dir = repo_root / "docs" / "journal"
    journal_entries: list[str] = []
    journal_non_entry_markdown: list[str] = []
    if journal_dir.is_dir():
        for path in sorted(journal_dir.glob("*.md")):
            if not path.is_file():
                continue
            if path.name in non_entry_files:
                continue
            if pattern.match(path.name):
                journal_entries.append(path.name)
            else:
                journal_non_entry_markdown.append(path.name)
    indexed_targets, noncanonical_lines, duplicate_targets = parse_journal_index(journal_dir / "index.md")
    journal_indexed = sorted(name for name in journal_entries if name in indexed_targets)
    journal_missing_from_index = sorted(name for name in journal_entries if name not in indexed_targets)
    journal_index_ok = not journal_missing_from_index and not noncanonical_lines and not duplicate_targets
    return {
        "journal_entry_regex": entry_regex,
        "journal_entries": journal_entries,
        "journal_non_entry_markdown": journal_non_entry_markdown,
        "journal_indexed": journal_indexed,
        "journal_missing_from_index": journal_missing_from_index,
        "journal_noncanonical_index_lines": noncanonical_lines,
        "journal_duplicate_index_targets": duplicate_targets,
        "journal_index_ok": journal_index_ok,
    }


def audit_archive(repo_root: Path, manifest: dict[str, object]) -> dict[str, object]:
    archive_cfg = manifest["archive"]
    assert isinstance(archive_cfg, dict)
    rollup_regex = str(archive_cfg["top_level_rollup_regex"])
    allowed_top_level_files = set(str(name) for name in archive_cfg["allowed_top_level_files"])
    pattern = re.compile(rollup_regex)
    archive_dir = repo_root / "docs" / "archive"
    top_level_files = sorted(path.name for path in archive_dir.glob("*.md") if path.is_file()) if archive_dir.is_dir() else []
    archive_non_rollup_top_level_files = sorted(
        name for name in top_level_files if name not in allowed_top_level_files and not pattern.match(name)
    )
    return {
        "archive_top_level_files": top_level_files,
        "archive_non_rollup_top_level_files": archive_non_rollup_top_level_files,
        "archive_ok": not archive_non_rollup_top_level_files,
    }


def audit_gitlinks(repo_root: Path) -> dict[str, object]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--stage"],
        check=True,
        capture_output=True,
        text=True,
    )
    gitlink_paths = sorted(
        line.split(maxsplit=3)[3]
        for line in result.stdout.splitlines()
        if line.startswith("160000 ")
    )
    forbidden_prefixes = (
        "services/",
        "experiments/",
        "layer-data/",
        "layer-gateway/",
        "layer-inference/",
        "layer-interface/",
        "layer-tools/",
    )
    forbidden_gitlink_paths = sorted(path for path in gitlink_paths if path.startswith(forbidden_prefixes))
    return {
        "gitlink_paths": gitlink_paths,
        "forbidden_gitlink_paths": forbidden_gitlink_paths,
        "gitlink_ok": not forbidden_gitlink_paths,
    }


def audit_repo(repo_root: Path, scope: str) -> dict[str, object]:
    errors: list[str] = []
    try:
        manifest = load_manifest(repo_root)
    except Exception as exc:  # pragma: no cover
        manifest = {}
        errors.append(str(exc))

    payload: dict[str, object] = {"errors": errors}
    if errors:
        payload.update(
            {
                "allowed_root_files": [],
                "unexpected_root_files": [],
                "root_ok": False,
                "journal_entry_regex": "",
                "journal_entries": [],
                "journal_non_entry_markdown": [],
                "journal_indexed": [],
                "journal_missing_from_index": [],
                "journal_noncanonical_index_lines": [],
                "journal_duplicate_index_targets": [],
                "journal_index_ok": False,
                "archive_top_level_files": [],
                "archive_non_rollup_top_level_files": [],
                "archive_ok": False,
                "gitlink_paths": [],
                "forbidden_gitlink_paths": [],
                "gitlink_ok": False,
                "overall_ok": False,
                "scope": scope,
            }
        )
        return payload

    root_payload = audit_root(repo_root, manifest)
    journal_payload = audit_journal(repo_root, manifest)
    archive_payload = audit_archive(repo_root, manifest)
    gitlink_payload = audit_gitlinks(repo_root)
    payload.update(root_payload)
    payload.update(journal_payload)
    payload.update(archive_payload)
    payload.update(gitlink_payload)

    scope_map = {
        "root": bool(payload["root_ok"]),
        "journal": bool(payload["journal_index_ok"]),
        "archive": bool(payload["archive_ok"]),
        "gitlinks": bool(payload["gitlink_ok"]),
    }
    if scope == "all":
        overall_ok = all(scope_map.values())
    else:
        overall_ok = scope_map[scope]
    payload["overall_ok"] = overall_ok and not errors
    payload["scope"] = scope
    return payload


def print_table(payload: dict[str, object]) -> None:
    print("repo_hygiene")
    print(f"scope: {payload['scope']}")
    print(f"root_ok: {'yes' if payload['root_ok'] else 'no'}")
    print("unexpected_root_files:")
    if payload["unexpected_root_files"]:
        for name in payload["unexpected_root_files"]:
            print(f"- {name}")
    else:
        print("-")
    print(f"journal_index_ok: {'yes' if payload['journal_index_ok'] else 'no'}")
    print("journal_missing_from_index:")
    if payload["journal_missing_from_index"]:
        for name in payload["journal_missing_from_index"]:
            print(f"- {name}")
    else:
        print("-")
    print("journal_noncanonical_index_lines:")
    if payload["journal_noncanonical_index_lines"]:
        for line in payload["journal_noncanonical_index_lines"]:
            print(f"- {line}")
    else:
        print("-")
    print(f"archive_ok: {'yes' if payload['archive_ok'] else 'no'}")
    print("archive_non_rollup_top_level_files:")
    if payload["archive_non_rollup_top_level_files"]:
        for name in payload["archive_non_rollup_top_level_files"]:
            print(f"- {name}")
    else:
        print("-")
    print(f"gitlink_ok: {'yes' if payload['gitlink_ok'] else 'no'}")
    print("forbidden_gitlink_paths:")
    if payload["forbidden_gitlink_paths"]:
        for name in payload["forbidden_gitlink_paths"]:
            print(f"- {name}")
    else:
        print("-")
    if payload["errors"]:
        print("errors:")
        for error in payload["errors"]:
            print(f"- {error}")
    print(f"overall_ok: {'yes' if payload['overall_ok'] else 'no'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Print JSON payload")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when the selected scope fails")
    parser.add_argument("--scope", choices=SCOPE_CHOICES, default="all", help="Contract scope to evaluate")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to the repo root to audit",
    )
    args = parser.parse_args()

    payload = audit_repo(Path(args.repo_root).resolve(), args.scope)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_table(payload)
    if args.strict and not payload["overall_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
