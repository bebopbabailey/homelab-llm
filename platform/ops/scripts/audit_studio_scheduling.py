#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any

from enforce_studio_launchd_policy import _remote_cmd, evaluate_policy
from validate_studio_policy import load_policy, validate_policy

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_POLICY = REPO_ROOT / "platform/ops/templates/studio_scheduling_policy.json"


def _policy_summary(policy: dict[str, Any]) -> dict[str, Any]:
    lane_defaults = policy.get("lane_defaults", {}) or {}
    managed = policy.get("managed_labels", {}) or {}
    retired = policy.get("retired_labels", {}) or {}
    return {
        "owned_namespaces": policy.get("owned_namespaces", []),
        "unmanaged_policy": policy.get("unmanaged_policy"),
        "quarantine_dir": policy.get("quarantine_dir", "/Library/LaunchDaemons/.quarantine"),
        "managed_labels": {
            label: {
                "lane": meta.get("lane"),
                "plist_path": meta.get("plist_path"),
                "required_keys": lane_defaults.get(meta.get("lane"), {}).get("required_keys", {}),
                "forbidden_keys": lane_defaults.get(meta.get("lane"), {}).get("forbidden_keys", []),
            }
            for label, meta in sorted(managed.items())
        },
        "retired_labels": sorted(retired.keys()),
        "utility_lane": policy.get("utility_lane", {}),
    }


def _managed_evidence(strict: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for label, data in sorted((strict.get("managed_checks") or {}).items()):
        report[label] = {
            "effective_required": data.get("effective_required", {}),
            "effective_forbidden_present": data.get("effective_forbidden_present", []),
            "required_missing": data.get("required_missing", []),
            "forbidden_absent": data.get("forbidden_absent", []),
            "evidence_source": data.get("evidence_source", ""),
            "compliant": data.get("compliant", data.get("ok", False)),
        }
    return report


def _collect_8100_runtime(studio_host: str, *, use_utility_wrapper: bool) -> dict[str, Any]:
    script = r'''
import json
import subprocess


def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def one_line(cmd):
    rc, out, _ = run(cmd)
    if rc != 0:
        return ""
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines[0] if lines else ""

listener_pid = one_line(["lsof", "-nP", "-tiTCP:8100", "-sTCP:LISTEN"])
listener_cmd = ""
ancestors = []
under_mlx_launch = False
under_launchd = False
is_vllm_listener = False

if listener_pid:
    listener_cmd = one_line(["ps", "-p", listener_pid, "-o", "command="])
    cmd_l = listener_cmd.lower()
    is_vllm_listener = " vllm serve " in f" {cmd_l} " or "bin/vllm serve" in cmd_l

    current = listener_pid
    seen = set()
    while current and current not in seen:
        seen.add(current)
        ppid = one_line(["ps", "-p", current, "-o", "ppid="])
        cmd = one_line(["ps", "-p", current, "-o", "command="])
        ancestors.append({"pid": current, "ppid": ppid, "command": cmd})
        cl = cmd.lower()
        if "/opt/mlx-launch/bin/start.sh" in cl or "com.bebop.mlx-launch" in cl:
            under_mlx_launch = True
        if not ppid or ppid == current or ppid == "1":
            if ppid == "1":
                root_cmd = one_line(["ps", "-p", "1", "-o", "command="])
                root_cmd_l = root_cmd.lower()
                under_launchd = "/sbin/launchd" in root_cmd_l or root_cmd_l == "launchd"
                ancestors.append({"pid": "1", "ppid": "0", "command": root_cmd})
            break
        current = ppid

payload = {
    "listener_pid": listener_pid or None,
    "listener_command": listener_cmd,
    "is_vllm_listener": is_vllm_listener,
    "under_mlx_launch": under_mlx_launch,
    "under_launchd": under_launchd,
    "ancestry": ancestors,
}
print(json.dumps(payload))
'''

    proc = _remote_cmd(
        studio_host,
        "python3 -",
        sudo=True,
        input_text=script,
        check=False,
        use_utility_wrapper=use_utility_wrapper,
    )
    if proc.returncode != 0:
        return {
            "listener_pid": None,
            "listener_command": "",
            "is_vllm_listener": False,
            "under_mlx_launch": False,
            "under_launchd": False,
            "ancestry": [],
            "error": (proc.stderr or "").strip() or "failed to inspect runtime",
        }

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {
            "listener_pid": None,
            "listener_command": "",
            "is_vllm_listener": False,
            "under_mlx_launch": False,
            "under_launchd": False,
            "ancestry": [],
            "error": "invalid runtime payload",
        }
    return data


def _runtime_8100_ok(runtime_8100: dict[str, Any]) -> bool:
    if not runtime_8100.get("listener_pid"):
        return False
    if not runtime_8100.get("is_vllm_listener"):
        return False
    # Current healthy Studio reality is per-lane launchd ownership. Retain
    # mlx-launch ancestry acceptance for older recovered states.
    return bool(runtime_8100.get("under_mlx_launch") or runtime_8100.get("under_launchd"))


def _observation_guidance() -> dict[str, Any]:
    return {
        "commands": [
            "ssh studio \"top -l 1 -o cpu -stats pid,command,cpu,mem | head -n 40\"",
            "ssh studio \"sudo -n powermetrics --samplers tasks --show-process-gpu -n 1 | rg -n 'vllm|optillm|GPU|task'\"",
            "ssh studio \"launchctl print system/com.bebop.mlx-launch | rg -n 'state =|pid =|program ='\"",
            "ssh studio \"launchctl print system/com.bebop.optillm-proxy | rg -n 'state =|pid =|program ='\""
        ],
        "good_looks_like": [
            "inference listeners stay owned by vllm serve under launchd-managed ancestry",
            "either direct per-lane launchd ownership or legacy mlx-launch ancestry is acceptable",
            "managed inference labels stay enabled and loaded",
            "transient maintenance/deploy commands run through utility clamp",
            "no unmanaged owned launchd labels are present"
        ],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit strict Studio scheduling policy compliance.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help="Policy manifest path")
    parser.add_argument("--host", default="studio", help="Studio SSH host")
    parser.add_argument("--policy-only", action="store_true", help="Validate policy locally without SSH")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument(
        "--no-utility-wrapper",
        action="store_true",
        help="Bypass studio_run_utility.sh and use direct ssh",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    use_utility_wrapper = not args.no_utility_wrapper

    try:
        policy = load_policy(args.policy)
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 1

    schema_errors = validate_policy(policy)
    if schema_errors:
        payload = {
            "ok": False,
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

    summary = _policy_summary(policy)

    if args.policy_only:
        payload = {
            "ok": True,
            "mode": "policy-only",
            "policy": str(args.policy),
            "summary": summary,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"policy-only audit ok: {args.policy}")
            print(json.dumps(summary, indent=2))
        return 0

    strict = evaluate_policy(policy, args.host, use_utility_wrapper=use_utility_wrapper)
    runtime_8100 = _collect_8100_runtime(args.host, use_utility_wrapper=use_utility_wrapper)

    runtime_ok = _runtime_8100_ok(runtime_8100)
    overall_ok = bool(strict.get("ok")) and runtime_ok

    payload = {
        "ok": overall_ok,
        "mode": "remote-audit",
        "policy": str(args.policy),
        "host": args.host,
        "use_utility_wrapper": use_utility_wrapper,
        "strict_policy": strict,
        "managed_label_evidence": _managed_evidence(strict),
        "runtime_8100": runtime_8100,
        "observation": _observation_guidance(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"host: {args.host}")
        print(f"policy: {args.policy}")
        print(f"strict policy ok: {strict.get('ok')}")
        print(f"runtime 8100 lineage ok: {runtime_ok}")
        print(f"overall ok: {overall_ok}")
        if strict.get("violations"):
            print("violations:")
            for v in strict["violations"]:
                print(f"- {v}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
