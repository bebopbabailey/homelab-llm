#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_POLICY = REPO_ROOT / "platform/ops/templates/studio_scheduling_policy.json"
LABEL_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def load_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"policy not found: {path}")
    data = json.loads(path.read_text() or "{}")
    if not isinstance(data, dict):
        raise ValueError("policy root must be an object")
    return data


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, bool)) and not isinstance(value, bool) or isinstance(value, bool)


def _validate_label_map(
    name: str,
    label_map: Any,
    owned_prefixes: list[str],
    lane_defaults: dict[str, Any],
    *,
    require_lane: bool,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(label_map, dict):
        return [f"{name} must be an object"]

    for label, meta in label_map.items():
        if not isinstance(label, str) or not LABEL_RE.match(label):
            errors.append(f"{name}: invalid label: {label!r}")
            continue
        if not any(label.startswith(prefix) for prefix in owned_prefixes):
            errors.append(f"{name}: label not in owned_namespaces: {label}")

        if not isinstance(meta, dict):
            errors.append(f"{name}.{label} must be an object")
            continue

        lane = meta.get("lane")
        if require_lane:
            if not isinstance(lane, str) or lane not in lane_defaults:
                errors.append(f"{name}.{label}.lane must be one of {sorted(lane_defaults)}")
            if lane == "retired":
                errors.append(f"{name}.{label} cannot use lane=retired; use retired_labels")

        plist_path = meta.get("plist_path")
        if plist_path is not None and not isinstance(plist_path, str):
            errors.append(f"{name}.{label}.plist_path must be a string when provided")

        plist_candidates = meta.get("plist_candidates")
        if plist_candidates is not None:
            if not isinstance(plist_candidates, list) or not all(isinstance(x, str) for x in plist_candidates):
                errors.append(f"{name}.{label}.plist_candidates must be a list of strings")

        action = meta.get("action")
        if action is not None and action not in {"quarantine", "ignore"}:
            errors.append(f"{name}.{label}.action must be quarantine|ignore when provided")

    return errors


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    version = policy.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append("version must be an integer >= 1")

    owned_namespaces = policy.get("owned_namespaces")
    if not isinstance(owned_namespaces, list) or not owned_namespaces:
        errors.append("owned_namespaces must be a non-empty list")
        owned_namespaces = []
    else:
        for prefix in owned_namespaces:
            if not isinstance(prefix, str) or not prefix:
                errors.append("owned_namespaces entries must be non-empty strings")
            elif not prefix.endswith("."):
                errors.append(f"owned_namespaces prefix should end with '.': {prefix}")

    unmanaged_policy = policy.get("unmanaged_policy")
    if unmanaged_policy not in {"quarantine", "fail_only", "remove"}:
        errors.append("unmanaged_policy must be one of quarantine|fail_only|remove")

    utility_lane = policy.get("utility_lane")
    if not isinstance(utility_lane, dict):
        errors.append("utility_lane must be an object")
    else:
        taskpolicy_args = utility_lane.get("taskpolicy_args")
        if not isinstance(taskpolicy_args, list) or not all(isinstance(x, str) for x in taskpolicy_args):
            errors.append("utility_lane.taskpolicy_args must be a list of strings")
        default_nice = utility_lane.get("default_nice")
        if not isinstance(default_nice, int):
            errors.append("utility_lane.default_nice must be an integer")

    lane_defaults = policy.get("lane_defaults")
    if not isinstance(lane_defaults, dict):
        errors.append("lane_defaults must be an object")
        lane_defaults = {}
    else:
        for lane in ("inference", "background", "retired"):
            if lane not in lane_defaults:
                errors.append(f"lane_defaults missing required lane: {lane}")

        for lane_name, lane_cfg in lane_defaults.items():
            if not isinstance(lane_cfg, dict):
                errors.append(f"lane_defaults.{lane_name} must be an object")
                continue
            if lane_name != "retired":
                required_keys = lane_cfg.get("required_keys")
                forbidden_keys = lane_cfg.get("forbidden_keys")
                if not isinstance(required_keys, dict):
                    errors.append(f"lane_defaults.{lane_name}.required_keys must be an object")
                else:
                    for key, value in required_keys.items():
                        if not isinstance(key, str) or not key:
                            errors.append(f"lane_defaults.{lane_name}.required_keys contains invalid key")
                        if not isinstance(value, (str, int, bool)):
                            errors.append(
                                f"lane_defaults.{lane_name}.required_keys.{key} must be string|int|bool"
                            )
                if not isinstance(forbidden_keys, list) or not all(isinstance(x, str) for x in forbidden_keys):
                    errors.append(f"lane_defaults.{lane_name}.forbidden_keys must be a list of strings")

    managed_labels = policy.get("managed_labels")
    retired_labels = policy.get("retired_labels")

    errors.extend(
        _validate_label_map(
            "managed_labels",
            managed_labels,
            owned_namespaces if isinstance(owned_namespaces, list) else [],
            lane_defaults if isinstance(lane_defaults, dict) else {},
            require_lane=True,
        )
    )
    errors.extend(
        _validate_label_map(
            "retired_labels",
            retired_labels,
            owned_namespaces if isinstance(owned_namespaces, list) else [],
            lane_defaults if isinstance(lane_defaults, dict) else {},
            require_lane=False,
        )
    )

    if isinstance(managed_labels, dict) and isinstance(retired_labels, dict):
        overlap = sorted(set(managed_labels) & set(retired_labels))
        if overlap:
            errors.append(f"labels cannot exist in both managed_labels and retired_labels: {', '.join(overlap)}")

    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate studio scheduling policy manifest.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help="Path to policy manifest")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        policy = load_policy(args.policy)
    except Exception as exc:  # pragma: no cover - command line UX
        if args.json:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 1

    errors = validate_policy(policy)
    ok = len(errors) == 0

    if args.json:
        print(
            json.dumps(
                {
                    "ok": ok,
                    "policy": str(args.policy),
                    "managed_count": len(policy.get("managed_labels", {}) or {}),
                    "retired_count": len(policy.get("retired_labels", {}) or {}),
                    "errors": errors,
                },
                indent=2,
            )
        )
    else:
        print(f"policy: {args.policy}")
        if ok:
            print("validation: ok")
        else:
            print("validation: failed")
            for err in errors:
                print(f"- {err}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
