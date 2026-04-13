#!/usr/bin/env python3
"""Run a structured failure probe against vllm-metal experimental lanes.

The probe drives requests through LiteLLM, monitors Studio lane state, and
captures evidence when a lane drops (listener gone / connection errors).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def percentile(values: List[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = (len(ordered) - 1) * (p / 100.0)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    left = ordered[lo]
    right = ordered[hi]
    return left + (right - left) * (idx - lo)


def run_cmd(cmd: List[str], timeout_s: int = 60) -> Dict[str, Any]:
    started = time.time()
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_s,
    )
    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "duration_s": round(time.time() - started, 3),
    }


def run_ssh(host: str, remote_cmd: str, timeout_s: int = 60) -> Dict[str, Any]:
    return run_cmd(["ssh", "-o", "BatchMode=yes", host, remote_cmd], timeout_s=timeout_s)


def load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must parse to a JSON object")
    return payload


def make_history_blob(chars: int) -> str:
    if chars <= 0:
        return ""
    base = (
        "This is prior assistant context for stress testing and should be treated "
        "as ordinary conversation history. "
    )
    out: List[str] = []
    total = 0
    while total < chars:
        out.append(base)
        total += len(base)
    return "".join(out)[:chars]


@dataclass
class ProbeConfig:
    litellm_chat_url: str
    litellm_health_url: str
    model: str
    token_env: str
    studio_host: str
    monitor_ports: List[int]
    stop_on_failure: bool
    scenarios: List[Dict[str, Any]]
    request_timeout_s: int


class Probe:
    def __init__(self, cfg: ProbeConfig, bearer: str | None):
        self.cfg = cfg
        self.bearer = bearer or os.getenv(cfg.token_env, "")
        if not self.bearer:
            raise RuntimeError(
                f"missing bearer token (provide --bearer or set {cfg.token_env})"
            )

    def studio_state(self) -> Dict[str, Any]:
        ports_pattern = "|".join([f":{p}" for p in self.cfg.monitor_ports])
        lsof = run_ssh(
            self.cfg.studio_host,
            f"lsof -nP -iTCP -sTCP:LISTEN | egrep '{ports_pattern}' || true",
            timeout_s=20,
        )
        ps = run_ssh(
            self.cfg.studio_host,
            "ps -eo pid,ppid,etime,%cpu,%mem,rss,command | "
            "egrep 'vllm serve|python3.*vllm|8120|8121|8122' | grep -v egrep || true",
            timeout_s=20,
        )

        listeners = {}
        for p in self.cfg.monitor_ports:
            listeners[str(p)] = f":{p} (LISTEN)" in lsof.get("stdout", "")

        return {
            "captured_at": utc_now(),
            "listeners": listeners,
            "lsof": lsof,
            "ps": ps,
        }

    def lite_health(self) -> Dict[str, Any]:
        started = time.time()
        req = request.Request(self.cfg.litellm_health_url, method="GET")
        try:
            with request.urlopen(req, timeout=self.cfg.request_timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return {
                    "ok": True,
                    "status": resp.status,
                    "latency_s": round(time.time() - started, 3),
                    "body_preview": raw[:500],
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "status": None,
                "latency_s": round(time.time() - started, 3),
                "error": repr(exc),
            }

    def send_one(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        started = time.time()
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.cfg.litellm_chat_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.bearer}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=self.cfg.request_timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            choices = parsed.get("choices", []) if isinstance(parsed, dict) else []
            usage = parsed.get("usage", {}) if isinstance(parsed, dict) else {}
            return {
                "ok": True,
                "status": 200,
                "latency_s": round(time.time() - started, 3),
                "choices": len(choices),
                "completion_tokens": usage.get("completion_tokens"),
                "has_error": False,
            }
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "status": exc.code,
                "latency_s": round(time.time() - started, 3),
                "error": raw[:500],
                "has_error": True,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "status": None,
                "latency_s": round(time.time() - started, 3),
                "error": repr(exc),
                "has_error": True,
            }

    def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        name = str(scenario.get("name", "unnamed"))
        concurrency = int(scenario.get("concurrency", 1))
        repeats = int(scenario.get("repeats", 1))
        n = int(scenario.get("n", 1))
        max_tokens = int(scenario.get("max_tokens", 64))
        temperature = float(scenario.get("temperature", 0.2))
        prompt = str(
            scenario.get(
                "prompt",
                "In one short sentence, describe a moonlit evening.",
            )
        )
        history_chars = int(scenario.get("history_chars", 0))

        history_blob = make_history_blob(history_chars)
        base_messages: List[Dict[str, str]] = []
        if history_blob:
            base_messages.append({"role": "assistant", "content": history_blob})
        base_messages.append({"role": "user", "content": prompt})

        request_payload = {
            "model": self.cfg.model,
            "messages": base_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "n": n,
        }

        all_results: List[Dict[str, Any]] = []
        batches: List[Dict[str, Any]] = []
        scenario_failed = False
        failure_reason = None

        for rep in range(1, repeats + 1):
            batch_started = time.time()
            batch_results: List[Dict[str, Any]] = []
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = [pool.submit(self.send_one, request_payload) for _ in range(concurrency)]
                for fut in as_completed(futures):
                    result = fut.result()
                    batch_results.append(result)
                    all_results.append(result)

            latencies = [r["latency_s"] for r in batch_results if isinstance(r.get("latency_s"), float)]
            success = sum(1 for r in batch_results if r.get("ok"))
            errors = len(batch_results) - success

            batch_summary = {
                "repeat": rep,
                "requests": len(batch_results),
                "success": success,
                "errors": errors,
                "p50_s": percentile(latencies, 50),
                "p95_s": percentile(latencies, 95),
                "duration_s": round(time.time() - batch_started, 3),
            }
            batches.append(batch_summary)

            if errors > 0:
                scenario_failed = True
                first_error = next((r for r in batch_results if not r.get("ok")), {})
                failure_reason = first_error.get("error")
                break

            state = self.studio_state()
            if not state["listeners"].get("8121", False):
                scenario_failed = True
                failure_reason = "8121 listener disappeared"
                break

        overall_latencies = [r["latency_s"] for r in all_results if isinstance(r.get("latency_s"), float)]
        overall_success = sum(1 for r in all_results if r.get("ok"))
        overall_errors = len(all_results) - overall_success

        return {
            "name": name,
            "request_shape": {
                "n": n,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "concurrency": concurrency,
                "repeats": repeats,
                "history_chars": history_chars,
                "prompt_preview": prompt[:200],
                "payload_preview": {
                    "model": request_payload["model"],
                    "messages_count": len(base_messages),
                    "stream": False,
                    "n": n,
                    "max_tokens": max_tokens,
                },
            },
            "batches": batches,
            "summary": {
                "requests": len(all_results),
                "success": overall_success,
                "errors": overall_errors,
                "p50_s": percentile(overall_latencies, 50),
                "p95_s": percentile(overall_latencies, 95),
                "failed": scenario_failed,
                "failure_reason": failure_reason,
            },
            "samples": {
                "first": all_results[0] if all_results else None,
                "first_error": next((r for r in all_results if not r.get("ok")), None),
            },
        }

    def capture_failure_evidence(self) -> Dict[str, Any]:
        studio_log = run_ssh(
            self.cfg.studio_host,
            "/usr/bin/log show --last 30m --style compact --predicate "
            "'eventMessage CONTAINS[c] \"8121\" OR eventMessage CONTAINS[c] \"vllm\" "
            "OR eventMessage CONTAINS[c] \"python3.12\" OR eventMessage CONTAINS[c] \"killed\" "
            "OR eventMessage CONTAINS[c] \"proc_exit\"' | tail -n 500",
            timeout_s=40,
        )
        mini_log = run_cmd(
            [
                "journalctl",
                "-u",
                "litellm-orch.service",
                "--since",
                "30 minutes ago",
                "--no-pager",
            ],
            timeout_s=40,
        )
        return {
            "captured_at": utc_now(),
            "studio_state": self.studio_state(),
            "studio_log": studio_log,
            "mini_litellm_log": {
                **mini_log,
                "stdout_tail": "\n".join(mini_log.get("stdout", "").splitlines()[-500:]),
            },
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe vllm-metal lane failure boundaries")
    parser.add_argument(
        "--profile",
        required=True,
        help="Path to probe profile JSON",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSON report path",
    )
    parser.add_argument(
        "--bearer",
        help="Optional bearer token override",
    )
    return parser.parse_args()


def build_config(profile: Dict[str, Any]) -> ProbeConfig:
    return ProbeConfig(
        litellm_chat_url=str(profile.get("litellm_chat_url", "http://127.0.0.1:4000/v1/chat/completions")),
        litellm_health_url=str(profile.get("litellm_health_url", "http://127.0.0.1:4000/health")),
        model=str(profile.get("model", "metal-test-main")),
        token_env=str(profile.get("token_env", "LITELLM_MASTER_KEY")),
        studio_host=str(profile.get("studio_host", "studio")),
        monitor_ports=[int(p) for p in profile.get("monitor_ports", [8120, 8121, 8122])],
        stop_on_failure=bool(profile.get("stop_on_failure", True)),
        scenarios=list(profile.get("scenarios", [])),
        request_timeout_s=int(profile.get("request_timeout_s", 180)),
    )


def main() -> int:
    args = parse_args()
    profile_path = Path(args.profile).resolve()
    out_path = Path(args.out).resolve()

    profile = load_json(profile_path)
    cfg = build_config(profile)
    probe = Probe(cfg, bearer=args.bearer)

    report: Dict[str, Any] = {
        "generated_at": utc_now(),
        "host": socket.gethostname(),
        "profile": str(profile_path),
        "config": {
            "litellm_chat_url": cfg.litellm_chat_url,
            "litellm_health_url": cfg.litellm_health_url,
            "model": cfg.model,
            "token_env": cfg.token_env,
            "studio_host": cfg.studio_host,
            "monitor_ports": cfg.monitor_ports,
            "stop_on_failure": cfg.stop_on_failure,
            "request_timeout_s": cfg.request_timeout_s,
        },
        "preflight": {
            "litellm_health": probe.lite_health(),
            "studio_state": probe.studio_state(),
        },
        "scenarios": [],
        "failure_evidence": None,
        "final": {},
    }

    probe_failed = False
    failed_scenario = None

    for scenario in cfg.scenarios:
        result = probe.run_scenario(scenario)
        report["scenarios"].append(result)

        if result["summary"]["failed"]:
            probe_failed = True
            failed_scenario = result["name"]
            if cfg.stop_on_failure:
                report["failure_evidence"] = probe.capture_failure_evidence()
                break

    report["final"] = {
        "probe_failed": probe_failed,
        "failed_scenario": failed_scenario,
        "completed_scenarios": len(report["scenarios"]),
        "total_scenarios": len(cfg.scenarios),
        "finished_at": utc_now(),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({
        "report_path": str(out_path),
        "probe_failed": probe_failed,
        "failed_scenario": failed_scenario,
        "completed_scenarios": len(report["scenarios"]),
        "total_scenarios": len(cfg.scenarios),
    }))
    return 1 if probe_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
