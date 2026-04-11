#!/usr/bin/env python3
"""Audit canonical service-registry coverage against discovered service roots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from service_registry import REGISTRY_PATH, load_entries


DISCOVERY_ROOTS = ("layer-data", "layer-gateway", "layer-inference", "layer-interface", "layer-tools", "services", "experiments")
REQUIRED_FIELDS = {
    "service_id",
    "path",
    "planned_path",
    "maturity",
    "runtime_mode",
    "service_kind",
    "host_targets",
    "exposure",
    "taxonomy_tags",
    "upstream_service_ids",
    "legacy_paths",
}


def gitlink_paths(repo_root: Path) -> set[str]:
    gitmodules = repo_root / ".gitmodules"
    paths: set[str] = set()
    if not gitmodules.is_file():
        return paths
    for line in gitmodules.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("path = "):
            paths.add(line.split("=", 1)[1].strip())
    return paths


def path_within_gitlink(path: str, gitlinks: set[str]) -> bool:
    return any(path == gitlink or path.startswith(f"{gitlink}/") for gitlink in gitlinks)


def discover_service_paths(repo_root: Path) -> list[str]:
    found: list[str] = []
    for root_name in DISCOVERY_ROOTS:
        root = repo_root / root_name
        if not root.is_dir():
            continue
        for spec in sorted(root.rglob("SERVICE_SPEC.md")):
            found.append(spec.parent.relative_to(repo_root).as_posix())
    return sorted(found)


def audit_registry(repo_root: Path) -> dict[str, object]:
    entries = load_entries(repo_root)
    discovered_paths = discover_service_paths(repo_root)
    gitlinks = gitlink_paths(repo_root)
    discovered_paths = sorted(set(discovered_paths) | gitlinks)
    errors: list[str] = []
    missing_required_fields: dict[str, list[str]] = {}
    duplicate_service_ids: list[str] = []
    duplicate_paths: list[str] = []
    service_ids_seen: set[str] = set()
    paths_seen: set[str] = set()
    entry_paths: list[str] = []

    for entry in entries:
        service_id = str(entry.get("service_id", ""))
        path = str(entry.get("path", ""))
        missing = sorted(field for field in REQUIRED_FIELDS if field not in entry)
        if missing:
            missing_required_fields[service_id or "<missing service_id>"] = missing
        if service_id in service_ids_seen:
            duplicate_service_ids.append(service_id)
        else:
            service_ids_seen.add(service_id)
        if path in paths_seen:
            duplicate_paths.append(path)
        else:
            paths_seen.add(path)
        entry_paths.append(path)
        target = repo_root / path
        if not target.exists() and not path_within_gitlink(path, gitlinks):
            errors.append(f"missing registry path: {path}")
        runtime_mode = str(entry.get("runtime_mode", ""))
        if runtime_mode != "docs-only" and not (target / "SERVICE_SPEC.md").is_file() and not path_within_gitlink(path, gitlinks):
            errors.append(f"path missing SERVICE_SPEC.md: {path}")

    missing_registry_entries = sorted(path for path in discovered_paths if path not in entry_paths)
    orphan_registry_entries = sorted(
        path for path in entry_paths if path not in discovered_paths and not path_within_gitlink(path, gitlinks)
    )
    overall_ok = (
        not errors
        and not missing_required_fields
        and not duplicate_service_ids
        and not duplicate_paths
        and not missing_registry_entries
        and not orphan_registry_entries
    )
    return {
        "registry_path": str(REGISTRY_PATH),
        "discovered_service_paths": discovered_paths,
        "registry_entry_count": len(entries),
        "missing_required_fields": missing_required_fields,
        "duplicate_service_ids": sorted(set(duplicate_service_ids)),
        "duplicate_paths": sorted(set(duplicate_paths)),
        "missing_registry_entries": missing_registry_entries,
        "orphan_registry_entries": orphan_registry_entries,
        "errors": errors,
        "overall_ok": overall_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    payload = audit_registry(Path(args.repo_root).resolve())
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    if args.strict and not payload["overall_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
