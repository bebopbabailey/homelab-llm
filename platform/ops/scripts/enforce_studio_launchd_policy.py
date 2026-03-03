#!/usr/bin/env python3
import argparse
import json
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from validate_studio_policy import load_policy, validate_policy

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_POLICY = REPO_ROOT / "platform/ops/templates/studio_scheduling_policy.json"
DEFAULT_WRAPPER = REPO_ROOT / "platform/ops/scripts/studio_run_utility.sh"
DEFAULT_QUARANTINE_DIR = "/Library/LaunchDaemons/.quarantine"
_DISABLED_RE = re.compile(r'"([^"]+)"\s*=>\s*(enabled|disabled)')


def _run(cmd: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr.strip()}"
        )
    return proc


def _wrapper_path() -> Path | None:
    candidate = Path(str(Path.cwd() / "platform/ops/scripts/studio_run_utility.sh"))
    if candidate.exists():
        return candidate
    if DEFAULT_WRAPPER.exists():
        return DEFAULT_WRAPPER
    return None


def _remote_cmd(
    studio_host: str,
    remote_cmd: str,
    *,
    sudo: bool = False,
    input_text: str | None = None,
    check: bool = True,
    use_utility_wrapper: bool = True,
) -> subprocess.CompletedProcess[str]:
    wrapper = _wrapper_path() if use_utility_wrapper else None
    if wrapper and wrapper.exists():
        cmd = [str(wrapper), "--host", studio_host]
        if sudo:
            cmd.append("--sudo")
        cmd.extend(["--", remote_cmd])
        return _run(cmd, input_text=input_text, check=check)

    prefix = "sudo -n bash -lc " if sudo else "bash -lc "
    ssh_cmd = prefix + shlex.quote(remote_cmd)
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ControlMaster=no",
        "-o",
        "ControlPath=none",
        studio_host,
        ssh_cmd,
    ]
    return _run(cmd, input_text=input_text, check=check)


def _extract_launchctl_disabled_map(studio_host: str, *, use_utility_wrapper: bool) -> dict[str, str]:
    proc = _remote_cmd(
        studio_host,
        "launchctl print-disabled system",
        sudo=True,
        check=False,
        use_utility_wrapper=use_utility_wrapper,
    )
    out = proc.stdout or ""
    result: dict[str, str] = {}
    for match in _DISABLED_RE.finditer(out):
        result[match.group(1)] = match.group(2)
    return result


def _label_from_plist_name(name: str) -> str | None:
    if ".plist.bak" in name:
        return None
    if name.endswith(".plist"):
        return name[: -len(".plist")]
    if name.endswith(".plist.disabled"):
        return name.split(".plist", 1)[0]
    return None


def _extract_installed_owned_paths(
    studio_host: str,
    owned_prefixes: list[str],
    *,
    use_utility_wrapper: bool,
) -> dict[str, list[str]]:
    proc = _remote_cmd(
        studio_host,
        "ls -1 /Library/LaunchDaemons 2>/dev/null || true",
        sudo=True,
        check=False,
        use_utility_wrapper=use_utility_wrapper,
    )
    mapping: dict[str, list[str]] = {}
    for raw in (proc.stdout or "").splitlines():
        name = raw.strip()
        if not name:
            continue
        label = _label_from_plist_name(name)
        if not label:
            continue
        if not any(label.startswith(prefix) for prefix in owned_prefixes):
            continue
        mapping.setdefault(label, []).append(f"/Library/LaunchDaemons/{name}")
    return mapping


def _plist_exists(studio_host: str, plist_path: str, *, use_utility_wrapper: bool) -> bool:
    proc = _remote_cmd(
        studio_host,
        f"test -f {shlex.quote(plist_path)}",
        sudo=True,
        check=False,
        use_utility_wrapper=use_utility_wrapper,
    )
    return proc.returncode == 0


def _parse_plistbuddy_scalar(raw: str) -> Any:
    value = raw.strip()
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def _read_plist_policy_keys(
    studio_host: str,
    plist_path: str,
    keys: list[str],
    *,
    use_utility_wrapper: bool,
) -> dict[str, Any]:
    json_cmd = f"plutil -convert json -o - {shlex.quote(plist_path)}"
    json_proc = _remote_cmd(
        studio_host,
        json_cmd,
        sudo=True,
        check=False,
        use_utility_wrapper=use_utility_wrapper,
    )

    if json_proc.returncode == 0:
        try:
            payload = json.loads(json_proc.stdout or "{}")
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            values = {key: payload[key] for key in keys if key in payload}
            return {
                "ok": True,
                "values": values,
                "present_keys": sorted(values.keys()),
                "evidence_source": f"plutil -convert json -o - {plist_path}",
                "method": "plutil-json",
            }

    values: dict[str, Any] = {}
    for key in keys:
        cmd = f"/usr/libexec/PlistBuddy -c {shlex.quote(f'Print :{key}')} {shlex.quote(plist_path)}"
        proc = _remote_cmd(
            studio_host,
            cmd,
            sudo=True,
            check=False,
            use_utility_wrapper=use_utility_wrapper,
        )
        if proc.returncode != 0:
            continue
        values[key] = _parse_plistbuddy_scalar((proc.stdout or "").strip())

    return {
        "ok": True,
        "values": values,
        "present_keys": sorted(values.keys()),
        "evidence_source": f"/usr/libexec/PlistBuddy Print :<key> {plist_path}",
        "method": "plistbuddy",
        "fallback_from": "plutil-json",
    }


def _normalize(raw: Any, expected: Any) -> Any:
    if raw is None:
        return None
    if isinstance(expected, bool):
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.lower() in {"1", "true", "yes"}
        return bool(raw)
    if isinstance(expected, int) and not isinstance(expected, bool):
        if isinstance(raw, int) and not isinstance(raw, bool):
            return raw
        try:
            return int(str(raw))
        except (ValueError, TypeError):
            return raw
    if isinstance(expected, str):
        return str(raw)
    return raw


def _pick_plist_path(label: str, entry: dict[str, Any], installed: dict[str, list[str]]) -> str | None:
    candidates: list[str] = []
    plist_path = entry.get("plist_path")
    if isinstance(plist_path, str):
        candidates.append(plist_path)
    plist_candidates = entry.get("plist_candidates") or []
    if isinstance(plist_candidates, list):
        candidates.extend([x for x in plist_candidates if isinstance(x, str)])
    candidates.extend(installed.get(label, []))

    for candidate in candidates:
        if candidate.endswith(".plist"):
            return candidate
    for candidate in candidates:
        if candidate.endswith(".plist.disabled"):
            return candidate
    return None


def evaluate_policy(
    policy: dict[str, Any],
    studio_host: str,
    *,
    use_utility_wrapper: bool,
    managed_label_filter: set[str] | None = None,
) -> dict[str, Any]:
    owned_prefixes = policy["owned_namespaces"]
    quarantine_dir = str(policy.get("quarantine_dir") or DEFAULT_QUARANTINE_DIR)
    managed = policy.get("managed_labels", {}) or {}
    retired = policy.get("retired_labels", {}) or {}
    lane_defaults = policy.get("lane_defaults", {}) or {}

    launchctl_disabled = _extract_launchctl_disabled_map(
        studio_host,
        use_utility_wrapper=use_utility_wrapper,
    )
    installed_paths = _extract_installed_owned_paths(
        studio_host,
        owned_prefixes,
        use_utility_wrapper=use_utility_wrapper,
    )

    disabled_owned_candidates = {
        label
        for label in launchctl_disabled
        if any(label.startswith(p) for p in owned_prefixes) and label not in installed_paths
    }
    discovered_disabled_owned: set[str] = set()
    for label in sorted(disabled_owned_candidates):
        loaded_proc = _remote_cmd(
            studio_host,
            f"launchctl print system/{shlex.quote(label)} >/dev/null 2>&1",
            sudo=True,
            check=False,
            use_utility_wrapper=use_utility_wrapper,
        )
        if loaded_proc.returncode == 0:
            discovered_disabled_owned.add(label)

    discovered_owned = set(installed_paths.keys()) | discovered_disabled_owned

    allowlisted = set(managed.keys()) | set(retired.keys())
    unmanaged = sorted(label for label in discovered_owned if label not in allowlisted)

    violations: list[str] = []
    unmanaged_details: dict[str, Any] = {}
    for label in unmanaged:
        state = launchctl_disabled.get(label, "unknown")
        loaded_proc = _remote_cmd(
            studio_host,
            f"launchctl print system/{shlex.quote(label)} >/dev/null 2>&1",
            sudo=True,
            check=False,
            use_utility_wrapper=use_utility_wrapper,
        )
        loaded = loaded_proc.returncode == 0
        paths = installed_paths.get(label, [])
        unmanaged_details[label] = {
            "state": state,
            "loaded": loaded,
            "plist_paths": paths,
        }
        violations.append(
            f"unmanaged owned label: {label} state={state} loaded={loaded} plist_paths={paths}"
        )

    if managed_label_filter:
        managed_items = {
            label: entry for label, entry in managed.items() if label in managed_label_filter
        }
    else:
        managed_items = managed

    managed_checks: dict[str, Any] = {}
    for label, entry in sorted(managed_items.items()):
        lane = entry.get("lane")
        lane_cfg = lane_defaults.get(lane, {})
        required = (lane_cfg.get("required_keys") or {}) if isinstance(lane_cfg, dict) else {}
        forbidden = (lane_cfg.get("forbidden_keys") or []) if isinstance(lane_cfg, dict) else []
        keys_to_check = sorted(set(required.keys()) | set(forbidden))

        state = launchctl_disabled.get(label, "unknown")
        loaded_proc = _remote_cmd(
            studio_host,
            f"launchctl print system/{shlex.quote(label)} >/dev/null 2>&1",
            sudo=True,
            check=False,
            use_utility_wrapper=use_utility_wrapper,
        )
        loaded = loaded_proc.returncode == 0

        plist_path = _pick_plist_path(label, entry, installed_paths)
        label_violations: list[str] = []
        key_values: dict[str, Any] = {}
        required_missing: list[str] = []
        required_present: list[str] = []
        required_mismatch: dict[str, Any] = {}
        forbidden_present: list[str] = []
        forbidden_absent: list[str] = []
        effective_required: dict[str, Any] = {}
        effective_forbidden_present: list[str] = []
        evidence_source = ""
        evidence_method = ""

        if state != "enabled":
            label_violations.append(f"expected enabled in launchctl print-disabled system, found: {state}")
        if not loaded:
            label_violations.append("expected loaded/runnable in launchctl system domain")

        if not plist_path:
            label_violations.append("no plist path discovered")
        else:
            if not _plist_exists(studio_host, plist_path, use_utility_wrapper=use_utility_wrapper):
                label_violations.append(f"plist missing: {plist_path}")
            else:
                plist_data = _read_plist_policy_keys(
                    studio_host,
                    plist_path,
                    keys_to_check,
                    use_utility_wrapper=use_utility_wrapper,
                )
                key_values = dict(plist_data.get("values", {}))
                evidence_source = str(plist_data.get("evidence_source", ""))
                evidence_method = str(plist_data.get("method", ""))

                for key, expected in required.items():
                    if key not in key_values:
                        effective_required[key] = None
                        required_missing.append(key)
                        label_violations.append(f"missing required key: {key}")
                        continue
                    required_present.append(key)
                    actual_raw = key_values[key]
                    effective_required[key] = actual_raw
                    actual = _normalize(actual_raw, expected)
                    if actual != expected:
                        required_mismatch[key] = {"expected": expected, "actual": actual_raw}
                        label_violations.append(
                            f"required key mismatch: {key} expected {expected!r} got {actual!r}"
                        )

                for key in forbidden:
                    if key not in key_values:
                        forbidden_absent.append(key)
                        continue
                    forbidden_present.append(key)
                    effective_forbidden_present.append(key)
                    label_violations.append(f"forbidden key present: {key}={key_values[key]!r}")

        violations.extend([f"{label}: {msg}" for msg in label_violations])
        managed_checks[label] = {
            "lane": lane,
            "state": state,
            "loaded": loaded,
            "plist_path": plist_path,
            "key_values": key_values,
            "effective_required": effective_required,
            "effective_forbidden_present": effective_forbidden_present,
            "required_present": sorted(required_present),
            "required_missing": sorted(required_missing),
            "required_mismatch": required_mismatch,
            "forbidden_present": sorted(forbidden_present),
            "forbidden_absent": sorted(forbidden_absent),
            "evidence_source": evidence_source,
            "evidence_method": evidence_method,
            "compliant": len(label_violations) == 0,
            "violations": label_violations,
            "ok": len(label_violations) == 0,
        }

    retired_checks: dict[str, Any] = {}
    for label, entry in sorted(retired.items()):
        state = launchctl_disabled.get(label, "unknown")
        loaded_proc = _remote_cmd(
            studio_host,
            f"launchctl print system/{shlex.quote(label)} >/dev/null 2>&1",
            sudo=True,
            check=False,
            use_utility_wrapper=use_utility_wrapper,
        )
        loaded = loaded_proc.returncode == 0
        plist_path = _pick_plist_path(label, entry, installed_paths)

        label_violations: list[str] = []
        if state != "disabled":
            label_violations.append(f"retired label must be disabled; found: {state}")
        if loaded:
            label_violations.append("retired label should not be loaded")

        violations.extend([f"{label}: {msg}" for msg in label_violations])
        retired_checks[label] = {
            "state": state,
            "loaded": loaded,
            "plist_path": plist_path,
            "violations": label_violations,
            "ok": len(label_violations) == 0,
            "action": entry.get("action", "quarantine"),
        }

    return {
        "studio_host": studio_host,
        "quarantine_dir": quarantine_dir,
        "discovered_owned_labels": sorted(discovered_owned),
        "unmanaged_owned_labels": unmanaged,
        "unmanaged_details": unmanaged_details,
        "installed_owned_paths": installed_paths,
        "launchctl_disabled_map": launchctl_disabled,
        "managed_checks": managed_checks,
        "retired_checks": retired_checks,
        "violations": violations,
        "ok": len(violations) == 0,
    }


def _plist_set_cmd(plist_path: str, key: str, value: Any) -> str:
    plist_q = shlex.quote(plist_path)
    key_q = shlex.quote(key)
    if isinstance(value, bool):
        val = "true" if value else "false"
        return (
            f"plutil -replace {key_q} -bool {val} {plist_q} >/dev/null 2>&1 "
            f"|| plutil -insert {key_q} -bool {val} {plist_q}"
        )
    if isinstance(value, int) and not isinstance(value, bool):
        return (
            f"plutil -replace {key_q} -integer {value} {plist_q} >/dev/null 2>&1 "
            f"|| plutil -insert {key_q} -integer {value} {plist_q}"
        )
    return (
        f"plutil -replace {key_q} -string {shlex.quote(str(value))} {plist_q} >/dev/null 2>&1 "
        f"|| plutil -insert {key_q} -string {shlex.quote(str(value))} {plist_q}"
    )


def _apply_managed_label(
    policy: dict[str, Any],
    studio_host: str,
    label: str,
    entry: dict[str, Any],
    installed_paths: dict[str, list[str]],
    timestamp: str,
    *,
    use_utility_wrapper: bool,
) -> dict[str, Any]:
    lane = entry["lane"]
    lane_cfg = policy["lane_defaults"][lane]
    required = lane_cfg.get("required_keys", {})
    forbidden = lane_cfg.get("forbidden_keys", [])
    plist_path = _pick_plist_path(label, entry, installed_paths)

    if not plist_path or not plist_path.endswith(".plist"):
        return {
            "label": label,
            "ok": False,
            "error": f"no writable plist path found for managed label: {label}",
        }

    backup_path = f"{plist_path}.bak.scheduling-policy.{timestamp}"
    commands: list[str] = [
        "set -euo pipefail",
        f"cp {shlex.quote(plist_path)} {shlex.quote(backup_path)}",
    ]

    for key, expected in required.items():
        commands.append(_plist_set_cmd(plist_path, key, expected))

    for key in forbidden:
        commands.append(f"plutil -remove {shlex.quote(key)} {shlex.quote(plist_path)} >/dev/null 2>&1 || true")

    commands.extend(
        [
            f"plutil -lint {shlex.quote(plist_path)} >/dev/null",
            f"launchctl enable system/{shlex.quote(label)} >/dev/null 2>&1 || true",
            f"launchctl bootout system {shlex.quote(plist_path)} >/dev/null 2>&1 || true",
            f"launchctl bootstrap system {shlex.quote(plist_path)}",
            f"launchctl kickstart -k system/{shlex.quote(label)}",
        ]
    )

    _remote_cmd(
        studio_host,
        "\n".join(commands),
        sudo=True,
        check=True,
        use_utility_wrapper=use_utility_wrapper,
    )

    return {
        "label": label,
        "ok": True,
        "plist_path": plist_path,
        "backup_path": backup_path,
    }


def _quarantine_label(
    studio_host: str,
    label: str,
    plist_paths: list[str],
    quarantine_dir: str,
    utc_timestamp: str,
    *,
    use_utility_wrapper: bool,
) -> dict[str, Any]:
    disable_proc = _remote_cmd(
        studio_host,
        f"launchctl disable system/{shlex.quote(label)}",
        sudo=True,
        check=False,
        use_utility_wrapper=use_utility_wrapper,
    )
    disable_ok = disable_proc.returncode == 0

    bootout_results = [
        _remote_cmd(
            studio_host,
            f"launchctl bootout system/{shlex.quote(label)}",
            sudo=True,
            check=False,
            use_utility_wrapper=use_utility_wrapper,
        ).returncode
        == 0
    ]

    original_candidates = [
        path
        for path in plist_paths
        if path.startswith("/Library/LaunchDaemons/") and path.endswith(".plist")
    ]
    original_path = original_candidates[0] if original_candidates else None

    if original_path:
        bootout_results.append(
            _remote_cmd(
                studio_host,
                f"launchctl bootout system {shlex.quote(original_path)}",
                sudo=True,
                check=False,
                use_utility_wrapper=use_utility_wrapper,
            ).returncode
            == 0
        )
    bootout_ok = any(bootout_results)

    quarantined_path = None
    move_ok = False
    move_error = ""

    if original_path:
        dest = f"{quarantine_dir}/{label}.plist.{utc_timestamp}"
        move_script = "\n".join(
            [
                "set -euo pipefail",
                f"install -d -o root -g wheel -m 0755 {shlex.quote(quarantine_dir)}",
                f"if [ ! -f {shlex.quote(original_path)} ]; then exit 10; fi",
                f"if [ -e {shlex.quote(dest)} ]; then exit 11; fi",
                f"mv {shlex.quote(original_path)} {shlex.quote(dest)}",
                f"echo {shlex.quote(dest)}",
            ]
        )
        move_proc = _remote_cmd(
            studio_host,
            move_script,
            sudo=True,
            check=False,
            use_utility_wrapper=use_utility_wrapper,
        )
        if move_proc.returncode == 0:
            move_ok = True
            quarantined_path = (move_proc.stdout or "").strip() or dest
        else:
            move_error = (move_proc.stderr or "").strip() or (move_proc.stdout or "").strip()

    return {
        "label": label,
        "ok": disable_ok and bootout_ok and (move_ok or original_path is None),
        "action": "quarantine",
        "original_path": original_path,
        "quarantined_path": quarantined_path,
        "disable_ok": disable_ok,
        "bootout_ok": bootout_ok,
        "move_ok": move_ok,
        "move_error": move_error,
        "plist_paths": plist_paths,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enforce strict Studio launchd scheduling policy.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help="Policy manifest path")
    parser.add_argument("--host", default="studio", help="Studio SSH host")
    parser.add_argument("--apply", action="store_true", help="Apply policy changes (default: check only)")
    parser.add_argument(
        "--managed-label",
        action="append",
        dest="managed_labels",
        help="Scope checks/applies to one managed label (repeatable)",
    )
    parser.add_argument(
        "--include-retired",
        action="store_true",
        help="When --apply is used, also enforce retired-label quarantine",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--no-utility-wrapper",
        action="store_true",
        help="Bypass studio_run_utility.sh and use direct ssh",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    mode = "apply" if args.apply else "check"
    use_utility_wrapper = not args.no_utility_wrapper

    try:
        policy = load_policy(args.policy)
    except Exception as exc:
        payload = {"ok": False, "mode": mode, "error": str(exc)}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 1

    schema_errors = validate_policy(policy)
    if schema_errors:
        payload = {
            "ok": False,
            "mode": mode,
            "policy": str(args.policy),
            "schema_errors": schema_errors,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("policy schema validation failed")
            for err in schema_errors:
                print(f"- {err}")
        return 1

    managed_filter = set(args.managed_labels or [])
    managed_all = set((policy.get("managed_labels") or {}).keys())
    unknown_filter = sorted(label for label in managed_filter if label not in managed_all)
    if unknown_filter:
        payload = {
            "ok": False,
            "mode": mode,
            "policy": str(args.policy),
            "error": f"unknown managed label(s): {', '.join(unknown_filter)}",
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["error"])
        return 1

    initial = evaluate_policy(
        policy,
        args.host,
        use_utility_wrapper=use_utility_wrapper,
        managed_label_filter=managed_filter or None,
    )
    actions: dict[str, Any] = {
        "managed_updates": [],
        "quarantined": [],
    }

    if args.apply:
        timestamp = time.strftime("%Y%m%d%H%M%S")
        utc_timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        quarantine_dir = str(policy.get("quarantine_dir") or DEFAULT_QUARANTINE_DIR)
        installed_paths = initial["installed_owned_paths"]

        if managed_filter:
            managed_entries = {
                label: entry
                for label, entry in (policy.get("managed_labels") or {}).items()
                if label in managed_filter
            }
        else:
            managed_entries = (policy.get("managed_labels") or {})

        for label, entry in sorted(managed_entries.items()):
            result = _apply_managed_label(
                policy,
                args.host,
                label,
                entry,
                installed_paths,
                timestamp,
                use_utility_wrapper=use_utility_wrapper,
            )
            actions["managed_updates"].append(result)

        unmanaged = initial["unmanaged_owned_labels"]
        if unmanaged and policy.get("unmanaged_policy") == "quarantine":
            for label in unmanaged:
                q = _quarantine_label(
                    args.host,
                    label,
                    initial["installed_owned_paths"].get(label, []),
                    quarantine_dir,
                    utc_timestamp,
                    use_utility_wrapper=use_utility_wrapper,
                )
                actions["quarantined"].append(q)

        if args.include_retired:
            for label in sorted((policy.get("retired_labels") or {}).keys()):
                q = _quarantine_label(
                    args.host,
                    label,
                    initial["installed_owned_paths"].get(label, []),
                    quarantine_dir,
                    utc_timestamp,
                    use_utility_wrapper=use_utility_wrapper,
                )
                actions["quarantined"].append(q)

    final = evaluate_policy(
        policy,
        args.host,
        use_utility_wrapper=use_utility_wrapper,
        managed_label_filter=managed_filter or None,
    )

    payload = {
        "ok": final["ok"],
        "mode": mode,
        "policy": str(args.policy),
        "host": args.host,
        "use_utility_wrapper": use_utility_wrapper,
        "initial": initial,
        "actions": actions,
        "final": final,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"mode: {mode}")
        print(f"host: {args.host}")
        print(f"policy: {args.policy}")
        print(f"violations: {len(final['violations'])}")
        for violation in final["violations"]:
            print(f"- {violation}")

    return 0 if final["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
