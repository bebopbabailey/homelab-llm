#!/usr/bin/env python3
"""Run repeated viability gates and aggregate confidence for decisions.

This script is intentionally orchestration-only. It wraps
`run_viability_gate.py`, captures logs/artifacts for each run, and emits a
campaign-level summary that highlights decision stability.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence


DECISION_GO = "GO"
DECISION_CONDITIONAL_GO = "CONDITIONAL_GO"
DECISION_NO_GO = "NO_GO"
DECISION_UNVERIFIED = "UNVERIFIED"

DEFAULT_CAMPAIGN_NAME = "optillm_mlx_campaign"
DEFAULT_RUNS = 3
DEFAULT_OUTPUT_DIR = "/tmp"
DEFAULT_SLEEP_SECONDS = 0.0

DECISION_PRIORITY = {
    DECISION_GO: 0,
    DECISION_CONDITIONAL_GO: 1,
    DECISION_UNVERIFIED: 2,
    DECISION_NO_GO: 3,
}

RETURN_CODE_TO_DECISION = {
    0: DECISION_GO,
    1: DECISION_NO_GO,
    2: DECISION_UNVERIFIED,
    3: DECISION_CONDITIONAL_GO,
}

DECISION_TO_RETURN_CODE = {
    DECISION_GO: 0,
    DECISION_CONDITIONAL_GO: 3,
    DECISION_UNVERIFIED: 2,
    DECISION_NO_GO: 1,
}


def run_cmd(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def parse_json_fragment(text: str) -> Dict[str, Any]:
    payload = text.strip()
    if not payload:
        return {}

    try:
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    starts = [idx for idx, char in enumerate(payload) if char == "{"]
    for idx in reversed(starts):
        fragment = payload[idx:]
        try:
            parsed = json.loads(fragment)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return {}


def decision_from_returncode(returncode: int) -> str:
    return RETURN_CODE_TO_DECISION.get(returncode, DECISION_UNVERIFIED)


def aggregate_decisions(decisions: Sequence[str]) -> Dict[str, Any]:
    counts = {
        DECISION_GO: 0,
        DECISION_CONDITIONAL_GO: 0,
        DECISION_UNVERIFIED: 0,
        DECISION_NO_GO: 0,
    }
    for decision in decisions:
        if decision in counts:
            counts[decision] += 1

    if not decisions:
        overall = DECISION_UNVERIFIED
    else:
        overall = max(decisions, key=lambda d: DECISION_PRIORITY.get(d, 999))

    unique = sorted(set(decisions))
    return {
        "overall_decision": overall,
        "decision_counts": counts,
        "decision_sequence": list(decisions),
        "decision_unique": unique,
        "stable": len(unique) <= 1 and bool(decisions),
    }


def collect_git_manifest(repo_root: Path) -> Dict[str, Any]:
    head = run_cmd(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    branch = run_cmd(["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"])
    status = run_cmd(["git", "-C", str(repo_root), "status", "--short"])

    return {
        "repo_root": str(repo_root),
        "git_head": head.stdout.strip() if head.returncode == 0 else None,
        "git_branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "git_status_short_preview": status.stdout.splitlines()[:20],
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repeated OptiLLM-on-MLX viability gates")
    parser.add_argument("--gate-config", required=True, help="Path to viability gate JSON config")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Number of repeated gate runs")
    parser.add_argument("--campaign-name", default=DEFAULT_CAMPAIGN_NAME)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--stop-on-no-go", action="store_true")
    parser.add_argument("--print-run-logs", action="store_true", help="Print gate stdout/stderr for each run")
    parser.add_argument("--quality-report", help="Optional quality report path passed through to gate")
    parser.add_argument("--quality-required", action="store_true")
    parser.add_argument("--bearer", help="Optional bearer token passed through to gate")
    args = parser.parse_args()

    if args.runs <= 0:
        raise SystemExit("--runs must be >= 1")
    if args.sleep_seconds < 0:
        raise SystemExit("--sleep-seconds must be >= 0")

    gate_config = Path(args.gate_config).resolve()
    if not gate_config.exists():
        raise SystemExit(f"--gate-config not found: {gate_config}")

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    gate_script = script_dir / "run_viability_gate.py"

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    campaign_dir = Path(args.output_dir).resolve() / f"{args.campaign_name}_{timestamp}"
    campaign_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": timestamp,
        "hostname": socket.gethostname(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "gate_script": str(gate_script),
        "gate_config": str(gate_config),
        "runs_requested": args.runs,
        "sleep_seconds": args.sleep_seconds,
        "stop_on_no_go": bool(args.stop_on_no_go),
        "print_run_logs": bool(args.print_run_logs),
        "quality_report": args.quality_report,
        "quality_required": bool(args.quality_required),
        "bearer_supplied": bool(args.bearer),
        "campaign_dir": str(campaign_dir),
        "git": collect_git_manifest(repo_root),
    }
    write_json(campaign_dir / "campaign_manifest.json", manifest)

    run_entries: List[Dict[str, Any]] = []
    decision_sequence: List[str] = []

    for idx in range(1, args.runs + 1):
        run_name = f"run_{idx:02d}"
        run_dir = campaign_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(gate_script),
            "--gate-config",
            str(gate_config),
            "--output-dir",
            str(run_dir),
        ]
        if args.quality_report:
            cmd += ["--quality-report", args.quality_report]
        if args.quality_required:
            cmd += ["--quality-required"]
        if args.bearer:
            cmd += ["--bearer", args.bearer]

        started_epoch = time.time()
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_epoch))
        completed = run_cmd(cmd)
        ended_epoch = time.time()
        ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ended_epoch))

        (run_dir / "gate.stdout.log").write_text(completed.stdout)
        (run_dir / "gate.stderr.log").write_text(completed.stderr)
        if args.print_run_logs:
            print(f"===== {run_name} gate stdout =====")
            if completed.stdout:
                print(completed.stdout.rstrip())
            else:
                print("<empty>")
            print(f"===== {run_name} gate stderr =====")
            if completed.stderr:
                print(completed.stderr.rstrip())
            else:
                print("<empty>")

        gate_output = parse_json_fragment(completed.stdout)
        write_json(run_dir / "gate_output.json", gate_output)

        decision = str(gate_output.get("final_decision") or decision_from_returncode(completed.returncode))
        decision_sequence.append(decision)

        report_path_value = gate_output.get("report_path")
        report_path: Path | None = None
        report_payload: Dict[str, Any] | None = None
        model_statuses: Dict[str, str] = {}
        if isinstance(report_path_value, str):
            report_path = Path(report_path_value)
            if report_path.exists():
                try:
                    report_payload = json.loads(report_path.read_text())
                except json.JSONDecodeError:
                    report_payload = None

        if isinstance(report_payload, dict):
            raw_statuses = report_payload.get("model_gate_status")
            if isinstance(raw_statuses, dict):
                for model, value in raw_statuses.items():
                    if isinstance(value, dict):
                        model_statuses[str(model)] = str(value.get("status", "unknown"))

        run_entry = {
            "run": run_name,
            "started_at": started,
            "ended_at": ended,
            "duration_seconds": round(ended_epoch - started_epoch, 3),
            "command": cmd,
            "returncode": completed.returncode,
            "decision": decision,
            "decision_reasons": gate_output.get("decision_reasons"),
            "report_path": str(report_path) if report_path else None,
            "model_gate_status": model_statuses,
            "stdout_log": str(run_dir / "gate.stdout.log"),
            "stderr_log": str(run_dir / "gate.stderr.log"),
            "gate_output_json": str(run_dir / "gate_output.json"),
        }
        run_entries.append(run_entry)

        if args.stop_on_no_go and decision == DECISION_NO_GO:
            break
        if idx < args.runs and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    decision_summary = aggregate_decisions(decision_sequence)
    campaign_summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "campaign_dir": str(campaign_dir),
        "gate_config": str(gate_config),
        "runs_requested": args.runs,
        "runs_completed": len(run_entries),
        "decision_summary": decision_summary,
        "runs": run_entries,
    }

    summary_path = campaign_dir / "campaign_summary.json"
    write_json(summary_path, campaign_summary)

    print(
        json.dumps(
            {
                "summary_path": str(summary_path),
                "campaign_dir": str(campaign_dir),
                "overall_decision": decision_summary["overall_decision"],
                "decision_counts": decision_summary["decision_counts"],
                "stable": decision_summary["stable"],
                "runs_completed": len(run_entries),
            },
            indent=2,
        )
    )

    overall = str(decision_summary["overall_decision"])
    return DECISION_TO_RETURN_CODE.get(overall, 2)


if __name__ == "__main__":
    raise SystemExit(main())
