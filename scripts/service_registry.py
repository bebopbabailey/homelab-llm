#!/usr/bin/env python3
"""Resolve service metadata from the canonical platform service registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REGISTRY_PATH = Path("platform/registry/services.jsonl")


def repo_root_from(path: Path | None = None) -> Path:
    return (path or Path.cwd()).resolve()


def load_entries(repo_root: Path | None = None) -> list[dict[str, object]]:
    root = repo_root_from(repo_root)
    path = root / REGISTRY_PATH
    entries: list[dict[str, object]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        row = json.loads(text)
        if not isinstance(row, dict):
            raise ValueError(f"{REGISTRY_PATH}:{lineno}: row must be a JSON object")
        entries.append(row)
    return entries


def entry_by_id(repo_root: Path | None, service_id: str) -> dict[str, object]:
    normalized = service_id.strip()
    for entry in load_entries(repo_root):
        if entry.get("service_id") == normalized:
            return entry
    raise KeyError(service_id)


def resolve_service_path(repo_root: Path | None, service_id: str) -> str:
    entry = entry_by_id(repo_root, service_id)
    path = entry.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError(f"service entry missing path: {service_id}")
    return path


def list_entries(entries: list[dict[str, object]], *, maturity: str | None = None) -> list[dict[str, object]]:
    if not maturity:
        return entries
    return [entry for entry in entries if entry.get("maturity") == maturity]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    show = subparsers.add_parser("show")
    show.add_argument("service_id")
    show.add_argument("--json", action="store_true")

    path = subparsers.add_parser("path")
    path.add_argument("service_id")

    list_cmd = subparsers.add_parser("list")
    list_cmd.add_argument("--maturity")
    list_cmd.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root_from(Path(__file__).resolve().parents[1])
    if args.command == "show":
        payload = entry_by_id(root, args.service_id)
        print(json.dumps(payload, indent=2) if args.json else json.dumps(payload))
        return 0
    if args.command == "path":
        print(resolve_service_path(root, args.service_id))
        return 0
    if args.command == "list":
        payload = list_entries(load_entries(root), maturity=args.maturity)
        print(json.dumps(payload, indent=2) if args.json else "\n".join(str(item["service_id"]) for item in payload))
        return 0
    raise SystemExit("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
