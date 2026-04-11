#!/usr/bin/env python3
"""Audit layer and service documentation contract coverage.

Usage:
  uv run python scripts/docs_contract_audit.py
  uv run python scripts/docs_contract_audit.py --json
  uv run python scripts/docs_contract_audit.py --strict --json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

SERVICE_REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "SERVICE_SPEC.md",
    "ARCHITECTURE.md",
    "AGENTS.md",
    "CONSTRAINTS.md",
    "RUNBOOK.md",
    "TASKS.md",
)
LAYER_REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "AGENTS.md",
    "CONSTRAINTS.md",
    "DEPENDENCIES.md",
    "RUNBOOK.md",
)
SERVICE_MARKERS: tuple[str, ...] = tuple(name for name in SERVICE_REQUIRED_FILES if name != "README.md")
EXCLUDED_DIR_NAMES: set[str] = {"docs"}
SERVICE_DISCOVERY_ROOTS: tuple[str, ...] = ("services", "experiments")


@dataclass
class DocAudit:
    path: str
    present: list[str]
    missing: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing


def _is_data_registry_dir(path: Path) -> bool:
    if path.name != "registry":
        return False
    entries = [entry.name for entry in path.iterdir() if not entry.name.startswith(".")]
    if not entries:
        return False
    has_jsonl = any(name.endswith(".jsonl") for name in entries)
    has_contract = any((path / marker).exists() for marker in SERVICE_MARKERS)
    return has_jsonl and not has_contract


def discover_layers(repo_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(repo_root.glob("layer-*"))
        if path.is_dir() and not path.name.startswith(".")
    ]


def discover_services(repo_root: Path) -> list[Path]:
    services: list[Path] = []
    for path in sorted(repo_root.glob("layer-*/*")):
        if not path.is_dir():
            continue
        if path.name.startswith(".") or path.name in EXCLUDED_DIR_NAMES:
            continue
        if _is_data_registry_dir(path):
            continue
        if not any((path / marker).exists() for marker in SERVICE_MARKERS):
            continue
        services.append(path)
    for root_name in SERVICE_DISCOVERY_ROOTS:
        root = repo_root / root_name
        if not root.is_dir():
            continue
        for spec in sorted(root.rglob("SERVICE_SPEC.md")):
            path = spec.parent
            rel_parts = path.relative_to(repo_root).parts
            if any(part.startswith(".") or part in EXCLUDED_DIR_NAMES for part in rel_parts):
                continue
            services.append(path)
    return sorted(set(services))


def audit_layers(repo_root: Path) -> list[DocAudit]:
    audits: list[DocAudit] = []
    for layer_dir in discover_layers(repo_root):
        present = [name for name in LAYER_REQUIRED_FILES if (layer_dir / name).exists()]
        missing = [name for name in LAYER_REQUIRED_FILES if name not in present]
        audits.append(DocAudit(path=str(layer_dir), present=present, missing=missing))
    return audits


def audit_services(repo_root: Path) -> list[DocAudit]:
    audits: list[DocAudit] = []
    for service_dir in discover_services(repo_root):
        present = [name for name in SERVICE_REQUIRED_FILES if (service_dir / name).exists()]
        missing = [name for name in SERVICE_REQUIRED_FILES if name not in present]
        audits.append(DocAudit(path=str(service_dir), present=present, missing=missing))
    return audits


def as_rows(audits: list[DocAudit]) -> list[dict[str, object]]:
    return [
        {
            "path": audit.path,
            "present": audit.present,
            "missing": audit.missing,
            "ok": audit.ok,
        }
        for audit in audits
    ]


def as_payload(service_audits: list[DocAudit], layer_audits: list[DocAudit]) -> dict[str, object]:
    services_with_gaps = sum(1 for audit in service_audits if not audit.ok)
    layers_with_gaps = sum(1 for audit in layer_audits if not audit.ok)
    services_ok = services_with_gaps == 0
    layers_ok = layers_with_gaps == 0
    services = [
        row for row in as_rows(service_audits)
    ]
    layers = [
        row for row in as_rows(layer_audits)
    ]
    return {
        "ok": services_ok,
        "required_files": list(SERVICE_REQUIRED_FILES),
        "service_count": len(service_audits),
        "services": services,
        "services_with_gaps": services_with_gaps,
        "required_layer_files": list(LAYER_REQUIRED_FILES),
        "layer_count": len(layer_audits),
        "layers": layers,
        "layers_with_gaps": layers_with_gaps,
        "layers_ok": layers_ok,
        "overall_ok": services_ok and layers_ok,
    }


def print_table(payload: dict[str, object]) -> None:
    print("service,ok,missing")
    for service in payload["services"]:
        assert isinstance(service, dict)
        missing = service["missing"]
        assert isinstance(missing, list)
        missing_text = "-" if not missing else "|".join(missing)
        print(f"{service['path']},{'yes' if service['ok'] else 'no'},{missing_text}")
    print()
    print(
        f"summary: service_count={payload['service_count']} "
        f"services_with_gaps={payload['services_with_gaps']} ok={payload['ok']}"
    )
    print()
    print("layer,ok,missing")
    for layer in payload["layers"]:
        assert isinstance(layer, dict)
        missing = layer["missing"]
        assert isinstance(missing, list)
        missing_text = "-" if not missing else "|".join(missing)
        print(f"{layer['path']},{'yes' if layer['ok'] else 'no'},{missing_text}")
    print()
    print(
        f"layer_summary: layer_count={payload['layer_count']} "
        f"layers_with_gaps={payload['layers_with_gaps']} layers_ok={payload['layers_ok']}"
    )
    print(f"overall_summary: overall_ok={payload['overall_ok']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Print JSON payload")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when gaps exist")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    payload = as_payload(audit_services(repo_root), audit_layers(repo_root))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_table(payload)
    if args.strict and not payload["overall_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
