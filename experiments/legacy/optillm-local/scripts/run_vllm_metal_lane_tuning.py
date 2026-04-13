#!/usr/bin/env python3
"""Run focused vLLM-metal lane tuning for max concurrency without crashes.

Phase A contract:
- direct-to-lane transport only (no LiteLLM in the measurement loop)
- fixed request shape across all candidates
- warmup requests are discarded
- quiescence gate before each candidate
- early reject from startup "Maximum concurrency..." signal
- minimal metrics only
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import re
import shlex
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error, request


KV_CACHE_RE = re.compile(r"GPU KV cache size:\s*([0-9,]+)\s*tokens")
MAX_CONCURRENCY_RE = re.compile(
    r"Maximum concurrency for\s*([0-9,]+)\s*tokens per request:\s*([0-9]*\.?[0-9]+)x"
)
VERSION_RE = re.compile(r"vLLM API server version\s*([^\s]+)")
ARGS_RE = re.compile(r"non-default args:\s*(\{.*\})")
METRIC_LINE_RE = re.compile(
    r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^}]*\})?\s+(-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)$"
)


def classify_ssh_error(raw_text: str, timed_out: bool = False) -> str:
    text = (raw_text or "").lower()
    if "system is locked" in text or "to unlock it" in text:
        return "LOCKED"
    if "permission denied" in text or "publickey" in text:
        return "AUTH_REJECTED"
    if (
        timed_out
        or "timed out" in text
        or "no route to host" in text
        or "network is unreachable" in text
        or "could not resolve hostname" in text
    ):
        return "HOST_DOWN"
    if "broken pipe" in text or "connection reset" in text:
        return "TRANSPORT_ERROR"
    return "UNKNOWN"


def map_ssh_error_to_host_state(ssh_error_class: Optional[str]) -> Dict[str, Optional[str]]:
    if ssh_error_class == "LOCKED":
        return {"host_state": "LOCKED", "ssh_error_class": "LOCKED"}
    if ssh_error_class == "AUTH_REJECTED":
        return {"host_state": "AUTH_BLOCKED", "ssh_error_class": "AUTH_REJECTED"}
    if ssh_error_class == "HOST_DOWN":
        return {"host_state": "UNREACHABLE", "ssh_error_class": "HOST_DOWN"}
    if ssh_error_class == "TRANSPORT_ERROR":
        return {"host_state": "UNSTABLE", "ssh_error_class": "TRANSPORT_ERROR"}
    return {"host_state": "READY", "ssh_error_class": None}


def classify_host_from_ready_and_evidence(
    ready: Dict[str, Any],
    failure_evidence: Optional[Dict[str, Any]],
) -> Dict[str, Optional[str]]:
    text_parts: List[str] = []
    for key in ("health_error", "models_error"):
        value = ready.get(key)
        if value:
            text_parts.append(str(value))
    if isinstance(failure_evidence, dict):
        for key in ("tail_log", "listeners", "processes"):
            node = failure_evidence.get(key)
            if isinstance(node, dict):
                stderr = node.get("stderr")
                stdout = node.get("stdout")
                if stderr:
                    text_parts.append(str(stderr))
                if stdout:
                    text_parts.append(str(stdout))
    joined = "\n".join(text_parts)
    ssh_error = classify_ssh_error(joined, timed_out=("timed out" in joined.lower()))
    mapped = map_ssh_error_to_host_state(ssh_error)
    if mapped["ssh_error_class"] is not None:
        return mapped
    if "connection refused" in joined.lower():
        return {"host_state": "READY", "ssh_error_class": "CONNECTION_REFUSED"}
    return {"host_state": "READY", "ssh_error_class": None}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
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
    try:
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
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = ""
        stderr = ""
        if isinstance(exc.stdout, bytes):
            stdout = exc.stdout.decode("utf-8", errors="replace")
        elif isinstance(exc.stdout, str):
            stdout = exc.stdout
        if isinstance(exc.stderr, bytes):
            stderr = exc.stderr.decode("utf-8", errors="replace")
        elif isinstance(exc.stderr, str):
            stderr = exc.stderr
        timeout_msg = f"Command timed out after {timeout_s}s"
        return {
            "cmd": cmd,
            "returncode": 124,
            "stdout": stdout,
            "stderr": (stderr + ("\n" if stderr else "") + timeout_msg).strip(),
            "duration_s": round(time.time() - started, 3),
            "timed_out": True,
        }


def run_ssh(host: str, remote_cmd: str, timeout_s: int = 120) -> Dict[str, Any]:
    return run_cmd(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "ControlMaster=no",
            "-o",
            "ControlPath=none",
            "-o",
            "ControlPersist=no",
            "-o",
            "ConnectTimeout=10",
            host,
            remote_cmd,
        ],
        timeout_s=timeout_s,
    )


def run_ssh_preflight(host: str, timeout_s: int = 20) -> Dict[str, Any]:
    probe = run_ssh(host, "echo codex_preflight_ready", timeout_s=timeout_s)
    if probe.get("returncode") == 0:
        return {
            "ok": True,
            "host_state": "READY",
            "ssh_error_class": None,
            "probe": probe,
        }
    err_text = "\n".join([str(probe.get("stderr", "")), str(probe.get("stdout", ""))])
    ssh_error = classify_ssh_error(err_text, timed_out=bool(probe.get("timed_out")))
    mapped = map_ssh_error_to_host_state(ssh_error)
    return {
        "ok": False,
        "host_state": mapped["host_state"],
        "ssh_error_class": mapped["ssh_error_class"],
        "probe": probe,
    }


def http_get_status(url: str, timeout_s: int) -> Dict[str, Any]:
    started = time.time()
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": resp.status,
                "latency_s": round(time.time() - started, 3),
                "body": body,
            }
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {
            "ok": False,
            "status": exc.code,
            "latency_s": round(time.time() - started, 3),
            "body": body,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": None,
            "latency_s": round(time.time() - started, 3),
            "error": repr(exc),
        }


def post_json(url: str, payload: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
    started = time.time()
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, method="POST", data=body)
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            usage = parsed.get("usage", {}) if isinstance(parsed, dict) else {}
            return {
                "ok": True,
                "status": resp.status,
                "latency_s": round(time.time() - started, 4),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
                "error": None,
            }
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {
            "ok": False,
            "status": exc.code,
            "latency_s": round(time.time() - started, 4),
            "completion_tokens": 0,
            "error": raw[:600],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": None,
            "latency_s": round(time.time() - started, 4),
            "completion_tokens": 0,
            "error": repr(exc),
        }


def parse_prometheus_metrics(raw: str) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = METRIC_LINE_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        val = float(match.group(2))
        values[name] = val
    return values


def first_metric_value(values: Dict[str, float], names: List[str]) -> Optional[float]:
    for name in names:
        if name in values:
            return values[name]
    return None


def poll_lane_metrics(
    metrics_url: str,
    timeout_s: int,
    running_names: List[str],
    waiting_names: List[str],
    kv_names: List[str],
) -> Dict[str, Any]:
    res = http_get_status(metrics_url, timeout_s=timeout_s)
    if not res.get("ok") or res.get("status") != 200:
        return {
            "ok": False,
            "status": res.get("status"),
            "running": None,
            "waiting": None,
            "kv_usage_perc": None,
            "error": res.get("error") or res.get("body", "")[:200],
        }
    parsed = parse_prometheus_metrics(str(res.get("body", "")))
    return {
        "ok": True,
        "status": 200,
        "running": first_metric_value(parsed, running_names),
        "waiting": first_metric_value(parsed, waiting_names),
        "kv_usage_perc": first_metric_value(parsed, kv_names),
    }


class MetricsPoller(threading.Thread):
    def __init__(
        self,
        metrics_url: str,
        poll_interval_s: float,
        timeout_s: int,
        running_names: List[str],
        waiting_names: List[str],
        kv_names: List[str],
    ) -> None:
        super().__init__(daemon=True)
        self.metrics_url = metrics_url
        self.poll_interval_s = poll_interval_s
        self.timeout_s = timeout_s
        self.running_names = running_names
        self.waiting_names = waiting_names
        self.kv_names = kv_names
        self.stop_event = threading.Event()
        self.samples: List[Dict[str, Any]] = []

    def run(self) -> None:
        while not self.stop_event.is_set():
            snapshot = poll_lane_metrics(
                metrics_url=self.metrics_url,
                timeout_s=self.timeout_s,
                running_names=self.running_names,
                waiting_names=self.waiting_names,
                kv_names=self.kv_names,
            )
            snapshot["captured_at"] = utc_now()
            self.samples.append(snapshot)
            self.stop_event.wait(self.poll_interval_s)

    def stop(self) -> None:
        self.stop_event.set()

    def summary(self) -> Dict[str, Any]:
        running = [float(s["running"]) for s in self.samples if s.get("running") is not None]
        waiting = [float(s["waiting"]) for s in self.samples if s.get("waiting") is not None]
        kv = [float(s["kv_usage_perc"]) for s in self.samples if s.get("kv_usage_perc") is not None]
        return {
            "samples": len(self.samples),
            "peak_running": max(running) if running else None,
            "peak_waiting": max(waiting) if waiting else None,
            "peak_kv_usage_perc": max(kv) if kv else None,
            "avg_running": round(sum(running) / len(running), 4) if running else None,
            "avg_waiting": round(sum(waiting) / len(waiting), 4) if waiting else None,
            "avg_kv_usage_perc": round(sum(kv) / len(kv), 4) if kv else None,
        }


def parse_startup_signals(log_text: str) -> Dict[str, Any]:
    kv_tokens = None
    max_conc_tokens = None
    max_conc_x = None
    version = None
    args_line = None

    for line in log_text.splitlines():
        if version is None:
            m = VERSION_RE.search(line)
            if m:
                version = m.group(1).strip()
        if args_line is None:
            m = ARGS_RE.search(line)
            if m:
                args_line = m.group(1).strip()
        if kv_tokens is None:
            m = KV_CACHE_RE.search(line)
            if m:
                kv_tokens = int(m.group(1).replace(",", ""))
        if max_conc_x is None:
            m = MAX_CONCURRENCY_RE.search(line)
            if m:
                max_conc_tokens = int(m.group(1).replace(",", ""))
                max_conc_x = float(m.group(2))

    return {
        "kv_cache_tokens": kv_tokens,
        "max_concurrency_tokens_per_request": max_conc_tokens,
        "max_concurrency_x": max_conc_x,
        "engine_version": version,
        "engine_args": args_line,
    }


def wait_until_ready(health_url: str, models_url: str, timeout_s: int) -> Dict[str, Any]:
    started = time.time()
    last_health: Dict[str, Any] = {}
    last_models: Dict[str, Any] = {}
    while time.time() - started < timeout_s:
        last_health = http_get_status(health_url, timeout_s=10)
        last_models = http_get_status(models_url, timeout_s=10)
        if last_health.get("status") == 200 and last_models.get("status") == 200:
            return {
                "ok": True,
                "wait_s": round(time.time() - started, 3),
                "health_status": 200,
                "models_status": 200,
            }
        time.sleep(1.0)
    return {
        "ok": False,
        "wait_s": round(time.time() - started, 3),
        "health_status": last_health.get("status"),
        "models_status": last_models.get("status"),
        "health_error": last_health.get("error"),
        "models_error": last_models.get("error"),
    }


def wait_for_quiescence(
    metrics_url: str,
    running_names: List[str],
    waiting_names: List[str],
    kv_names: List[str],
    timeout_s: int,
    stable_window_s: int,
) -> Dict[str, Any]:
    started = time.time()
    stable_started: Optional[float] = None
    observed: List[Dict[str, Any]] = []

    while time.time() - started < timeout_s:
        snap = poll_lane_metrics(
            metrics_url=metrics_url,
            timeout_s=10,
            running_names=running_names,
            waiting_names=waiting_names,
            kv_names=kv_names,
        )
        observed.append(snap)
        running = snap.get("running")
        waiting = snap.get("waiting")

        if running is not None and waiting is not None and running <= 0.0 and waiting <= 0.0:
            if stable_started is None:
                stable_started = time.time()
            if time.time() - stable_started >= stable_window_s:
                return {
                    "ok": True,
                    "wait_s": round(time.time() - started, 3),
                    "stable_window_s": stable_window_s,
                    "last_snapshot": snap,
                }
        else:
            stable_started = None

        time.sleep(1.0)

    return {
        "ok": False,
        "wait_s": round(time.time() - started, 3),
        "stable_window_s": stable_window_s,
        "last_snapshot": observed[-1] if observed else None,
        "reason": "timed_out_waiting_for_quiescence",
    }


def run_request_stage(
    chat_url: str,
    payload: Dict[str, Any],
    concurrency: int,
    requests_per_stage: int,
    request_timeout_s: int,
    stage_timeout_s: int,
) -> Dict[str, Any]:
    started = time.time()
    results: List[Dict[str, Any]] = []
    timed_out = False
    fail_fast_triggered = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        submitted = 0
        futures: set[concurrent.futures.Future] = set()

        while submitted < requests_per_stage and len(futures) < concurrency:
            futures.add(pool.submit(post_json, chat_url, payload, request_timeout_s))
            submitted += 1

        while futures:
            elapsed = time.time() - started
            remaining = max(stage_timeout_s - elapsed, 0.0)
            if remaining <= 0.0:
                timed_out = True
                for fut in futures:
                    fut.cancel()
                break

            done, pending = concurrent.futures.wait(
                futures,
                timeout=min(remaining, 1.0),
                return_when=concurrent.futures.FIRST_COMPLETED,
            )

            if not done:
                continue

            for fut in done:
                try:
                    item = fut.result()
                except Exception as exc:  # noqa: BLE001
                    item = {
                        "ok": False,
                        "status": None,
                        "latency_s": 0.0,
                        "completion_tokens": 0,
                        "error": repr(exc),
                    }
                results.append(item)
                if not item.get("ok", False):
                    fail_fast_triggered = True

            futures = set(pending)

            if fail_fast_triggered:
                for fut in futures:
                    fut.cancel()
                break

            while submitted < requests_per_stage and len(futures) < concurrency:
                futures.add(pool.submit(post_json, chat_url, payload, request_timeout_s))
                submitted += 1

    completed = len(results)
    status_counts: Dict[str, int] = {}
    for item in results:
        key = str(item.get("status"))
        status_counts[key] = status_counts.get(key, 0) + 1

    latencies = [float(item["latency_s"]) for item in results if item.get("latency_s") is not None]
    completion_tokens = sum(int(item.get("completion_tokens") or 0) for item in results)
    wall_s = max(time.time() - started, 1e-9)
    passed = (not timed_out) and completed == requests_per_stage and status_counts.get("200", 0) == requests_per_stage

    failures = [item for item in results if not item.get("ok")]
    return {
        "concurrency": concurrency,
        "requests_target": requests_per_stage,
        "requests_completed": completed,
        "timed_out": timed_out,
        "fail_fast_triggered": fail_fast_triggered,
        "status_counts": status_counts,
        "p50_latency_s": percentile(latencies, 50),
        "p95_latency_s": percentile(latencies, 95),
        "completion_tokens_total": completion_tokens,
        "tokens_per_sec": round(completion_tokens / wall_s, 4),
        "stage_wall_s": round(wall_s, 4),
        "passed": passed,
        "sample_errors": [f.get("error") for f in failures[:3]],
        "raw_results": results,
    }


def capture_failure_evidence(
    studio_host: str,
    log_path: str,
    monitor_ports: List[int],
) -> Dict[str, Any]:
    ports_pattern = "|".join([f":{p}" for p in monitor_ports])
    return {
        "captured_at": utc_now(),
        "tail_log": run_ssh(studio_host, f"tail -n 200 {shlex.quote(log_path)} || true", timeout_s=45),
        "listeners": run_ssh(
            studio_host,
            f"lsof -nP -iTCP -sTCP:LISTEN | egrep '{ports_pattern}' || true",
            timeout_s=30,
        ),
        "processes": run_ssh(
            studio_host,
            "ps -eo pid,ppid,etime,%cpu,%mem,rss,command | egrep 'vllm serve|python3.*vllm|8120|8121|8122' | grep -v egrep || true",
            timeout_s=30,
        ),
    }


def kill_remote_port_listeners(studio_host: str, port: int) -> Dict[str, Any]:
    return run_ssh(
        studio_host,
        (
            f"pids=$(lsof -ti tcp:{port} -sTCP:LISTEN || true); "
            "if [ -n \"$pids\" ]; then kill -9 $pids || true; fi; "
            f"lsof -nP -iTCP:{port} -sTCP:LISTEN || true"
        ),
        timeout_s=45,
    )


@dataclass
class Candidate:
    candidate_id: str
    phase: str
    max_model_len: int
    memory_fraction: str
    async_mode: str
    is_reference: bool = False


def build_phase_a_candidates(profile: Dict[str, Any]) -> List[Candidate]:
    phase = profile["phase_a"]
    async_mode = str(phase.get("async_mode", "off")).lower()
    seen = set()
    candidates: List[Candidate] = []

    if bool(phase.get("include_baseline_reference", True)):
        baseline = phase.get("baseline_reference", {})
        b_ml = int(baseline.get("max_model_len", 262144))
        b_mem = str(baseline.get("memory_fraction", "auto"))
        key = (b_ml, b_mem, async_mode, True)
        seen.add(key)
        candidates.append(
            Candidate(
                candidate_id=f"ref-ml{b_ml}-mem{b_mem}-async-{async_mode}",
                phase="phaseA",
                max_model_len=b_ml,
                memory_fraction=b_mem,
                async_mode=async_mode,
                is_reference=True,
            )
        )

    for max_model_len in phase.get("max_model_len_candidates", []):
        for mem_fraction in phase.get("memory_fraction_candidates", []):
            ml = int(max_model_len)
            mem = str(mem_fraction)
            key = (ml, mem, async_mode, False)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                Candidate(
                    candidate_id=f"a-ml{ml}-mem{mem}-async-{async_mode}",
                    phase="phaseA",
                    max_model_len=ml,
                    memory_fraction=mem,
                    async_mode=async_mode,
                )
            )
    return candidates


def build_phase_b_candidates(profile: Dict[str, Any]) -> List[Candidate]:
    phase = profile.get("phase_b", {})
    shortlist = phase.get("shortlist", [])
    async_mode = str(phase.get("async_mode", "on")).lower()
    candidates: List[Candidate] = []
    for idx, item in enumerate(shortlist):
        candidates.append(
            Candidate(
                candidate_id=str(item.get("candidate_id", f"b{idx+1}")),
                phase="phaseB",
                max_model_len=int(item["max_model_len"]),
                memory_fraction=str(item["memory_fraction"]),
                async_mode=async_mode,
            )
        )
    return candidates


def rank_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key_fn(item: Dict[str, Any]) -> Any:
        passed = 0 if item.get("pass_fail") == "PASS" else 1
        max_conc = item.get("startup", {}).get("max_concurrency_x")
        max_conc_sort = -float(max_conc) if max_conc is not None else float("inf")
        p95_c4 = item.get("summary", {}).get("p95_latency_s_at_c4")
        p95_sort = float(p95_c4) if p95_c4 is not None else float("inf")
        peak_kv = item.get("summary", {}).get("peak_kv_usage_perc")
        kv_sort = float(peak_kv) if peak_kv is not None else float("inf")
        return (passed, max_conc_sort, p95_sort, kv_sort, item.get("candidate_id", "zzz"))

    ordered = sorted(results, key=key_fn)
    for idx, item in enumerate(ordered, start=1):
        item["rank"] = idx
    return ordered


def write_markdown_summary(report: Dict[str, Any], out_md_path: Path) -> None:
    lines: List[str] = []
    lines.append("# vLLM-metal lane tuning summary")
    lines.append("")
    lines.append(f"- generated_at: `{report.get('generated_at')}`")
    lines.append(f"- mode: `{report.get('mode')}`")
    lines.append(f"- target lane: `{report.get('lane', {}).get('name')}` (`{report.get('lane', {}).get('port')}`)")
    lines.append("")
    lines.append("## Ranked scorecard")
    lines.append("")
    lines.append("| rank | candidate | pass | host_state | ssh_error | max_model_len | mem_fraction | async | startup_max_conc_x | startup_kv_tokens | p95@c4 (s) | peak_waiting | peak_kv_usage_perc | notes |")
    lines.append("|---:|---|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---|")
    for item in report.get("ranked_candidates", []):
        startup = item.get("startup", {})
        summary = item.get("summary", {})
        notes = item.get("notes", "")
        lines.append(
            "| {rank} | {cid} | {pf} | {hs} | {se} | {ml} | {mem} | {am} | {mc} | {kv} | {p95} | {pw} | {pkv} | {notes} |".format(
                rank=item.get("rank", ""),
                cid=item.get("candidate_id", ""),
                pf=item.get("pass_fail", ""),
                hs=item.get("host_state", "n/a"),
                se=item.get("ssh_error_class", "n/a"),
                ml=item.get("max_model_len", ""),
                mem=item.get("memory_fraction", ""),
                am=item.get("async_mode", ""),
                mc=startup.get("max_concurrency_x", "n/a"),
                kv=startup.get("kv_cache_tokens", "n/a"),
                p95=summary.get("p95_latency_s_at_c4", "n/a"),
                pw=summary.get("peak_waiting", "n/a"),
                pkv=summary.get("peak_kv_usage_perc", "n/a"),
                notes=notes or "",
            )
        )
    lines.append("")
    winner = report.get("winner")
    lines.append(f"## Winner")
    lines.append("")
    lines.append(f"`{winner}`" if winner else "No stable winner.")
    lines.append("")
    out_md_path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune vLLM-metal lane configs")
    parser.add_argument("--profile", required=True, help="Path to tuning profile JSON")
    parser.add_argument("--out", required=True, help="Output report JSON path")
    parser.add_argument("--mode", default="phaseA", choices=["phaseA", "phaseB", "all"])
    return parser.parse_args()


def load_profile(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("profile must be a JSON object")
    return payload


def candidate_notes(candidate: Candidate, early_reject: bool, skipped_c4: bool) -> str:
    notes: List[str] = []
    if candidate.is_reference:
        notes.append("reference")
    if early_reject:
        notes.append("early_reject_triggered")
    if skipped_c4:
        notes.append("skipped_c4")
    return ",".join(notes)


def build_payload_from_shape(request_shape: Dict[str, Any]) -> Dict[str, Any]:
    if "payload" in request_shape:
        payload = request_shape["payload"]
        if not isinstance(payload, dict):
            raise ValueError("fixed_request_shape.payload must be a JSON object")
        return payload

    history_chars = int(request_shape.get("history_chars", 0))
    history_unit = str(
        request_shape.get(
            "history_unit_text",
            "This is fixed synthetic prior context used for deterministic load testing. ",
        )
    )
    history_blob = ""
    if history_chars > 0:
        repeats = (history_chars // len(history_unit)) + 2
        history_blob = (history_unit * repeats)[:history_chars]

    messages: List[Dict[str, str]] = []
    system_prompt = request_shape.get("system_prompt")
    if system_prompt:
        messages.append({"role": "system", "content": str(system_prompt)})
    if history_blob:
        messages.append({"role": "assistant", "content": history_blob})
    user_prompt = str(
        request_shape.get(
            "user_prompt",
            "Return exactly one sentence describing a moonlit scene.",
        )
    )
    messages.append({"role": "user", "content": user_prompt})

    payload: Dict[str, Any] = {
        "model": str(request_shape.get("model", "default_model")),
        "messages": messages,
        "max_tokens": int(request_shape.get("max_tokens", 768)),
        "temperature": float(request_shape.get("temperature", 0.2)),
        "top_p": float(request_shape.get("top_p", 0.95)),
        "stream": False,
        "n": int(request_shape.get("n", 1)),
    }
    if "top_k" in request_shape:
        payload["top_k"] = int(request_shape["top_k"])
    if isinstance(request_shape.get("extra_payload_fields"), dict):
        payload.update(request_shape["extra_payload_fields"])
    return payload


def execute_candidate(
    candidate: Candidate,
    profile: Dict[str, Any],
    lane: Dict[str, Any],
    metrics_names: Dict[str, List[str]],
    request_shape: Dict[str, Any],
    budgets: Dict[str, Any],
    monitor_ports: List[int],
) -> Dict[str, Any]:
    studio_host = str(profile["target_host"])
    launch_template = str(lane["launch_template"])
    log_path = str(lane["log_path"])
    port = int(lane["port"])
    health_url = str(lane["health_url"])
    models_url = str(lane["models_url"])
    chat_url = str(lane["chat_url"])
    metrics_url = str(lane["metrics_url"])
    early_reject_floor = float(profile.get("early_reject", {}).get("max_concurrency_floor_x", 1.2))

    request_timeout_s = int(request_shape.get("request_timeout_s", 300))
    warmup_requests = int(request_shape.get("warmup_requests", 2))
    requests_per_stage = int(request_shape.get("requests_per_stage", 8))
    concurrency_sweep = [int(x) for x in request_shape.get("concurrency_sweep", [1, 2, 4])]
    payload = build_payload_from_shape(request_shape)

    candidate_started = time.time()
    preflight = run_ssh_preflight(studio_host, timeout_s=int(budgets.get("preflight_timeout_s", 20)))
    preflight_ok = bool(preflight.get("ok"))
    host_state = str(preflight.get("host_state", "READY"))
    ssh_error_class = preflight.get("ssh_error_class")
    if not preflight_ok:
        return {
            "candidate_id": candidate.candidate_id,
            "phase": candidate.phase,
            "max_model_len": candidate.max_model_len,
            "memory_fraction": candidate.memory_fraction,
            "async_mode": candidate.async_mode,
            "preflight_ok": False,
            "host_state": host_state,
            "ssh_error_class": ssh_error_class,
            "preflight": preflight.get("probe"),
            "pass_fail": "FAIL",
            "launch": None,
            "pre_kill": None,
            "ready": None,
            "startup": {},
            "early_reject_floor_x": early_reject_floor,
            "early_reject_triggered": False,
            "warmup": None,
            "stages": [],
            "summary": {
                "failure_reason": "ssh_preflight_failed",
                "candidate_wall_s": round(time.time() - candidate_started, 3),
            },
            "failure_evidence": {
                "preflight_probe": preflight.get("probe"),
                "captured_at": utc_now(),
            },
            "notes": candidate_notes(candidate, early_reject=False, skipped_c4=False),
        }
    async_flag = "--async-scheduling" if candidate.async_mode == "on" else "--no-async-scheduling"
    launch_cmd = launch_template.format(
        model_path=lane["model_path"],
        served_model_name=lane.get("served_model_name", "default_model"),
        port=port,
        max_model_len=candidate.max_model_len,
        memory_fraction=candidate.memory_fraction,
        async_flag=async_flag,
        log_path=log_path,
    )

    pre_kill_res = kill_remote_port_listeners(studio_host=studio_host, port=port)
    launch_res = run_ssh(studio_host, launch_cmd, timeout_s=int(budgets.get("restart_timeout_s", 180)))
    ready_res = wait_until_ready(
        health_url=health_url,
        models_url=models_url,
        timeout_s=int(budgets.get("startup_ready_timeout_s", 180)),
    )

    log_tail = run_ssh(studio_host, f"tail -n 400 {shlex.quote(log_path)} || true", timeout_s=45)
    startup = parse_startup_signals(log_tail.get("stdout", ""))

    early_reject = False
    if startup.get("max_concurrency_x") is not None and float(startup["max_concurrency_x"]) < early_reject_floor:
        early_reject = True

    result: Dict[str, Any] = {
        "candidate_id": candidate.candidate_id,
        "phase": candidate.phase,
        "max_model_len": candidate.max_model_len,
        "memory_fraction": candidate.memory_fraction,
        "async_mode": candidate.async_mode,
        "preflight_ok": preflight_ok,
        "host_state": host_state,
        "ssh_error_class": ssh_error_class,
        "preflight": preflight.get("probe"),
        "pass_fail": "FAIL",
        "launch": launch_res,
        "pre_kill": pre_kill_res,
        "ready": ready_res,
        "startup": startup,
        "early_reject_floor_x": early_reject_floor,
        "early_reject_triggered": early_reject,
        "warmup": None,
        "stages": [],
        "summary": {},
        "failure_evidence": None,
        "notes": "",
    }

    if not ready_res.get("ok"):
        failure_evidence = capture_failure_evidence(studio_host, log_path, monitor_ports)
        classification = classify_host_from_ready_and_evidence(ready_res, failure_evidence)
        result["host_state"] = classification["host_state"]
        result["ssh_error_class"] = classification["ssh_error_class"]
        result["summary"] = {
            "failure_reason": "lane_not_ready",
            "candidate_wall_s": round(time.time() - candidate_started, 3),
        }
        result["failure_evidence"] = failure_evidence
        result["notes"] = candidate_notes(candidate, early_reject, skipped_c4=False)
        return result

    quiescence = wait_for_quiescence(
        metrics_url=metrics_url,
        running_names=metrics_names["running"],
        waiting_names=metrics_names["waiting"],
        kv_names=metrics_names["kv_usage_perc"],
        timeout_s=int(budgets.get("quiescence_timeout_s", 120)),
        stable_window_s=int(budgets.get("quiescence_window_s", 10)),
    )
    result["quiescence"] = quiescence
    if not quiescence.get("ok"):
        failure_evidence = capture_failure_evidence(studio_host, log_path, monitor_ports)
        classification = classify_host_from_ready_and_evidence(ready_res, failure_evidence)
        result["host_state"] = classification["host_state"]
        result["ssh_error_class"] = classification["ssh_error_class"]
        result["summary"] = {
            "failure_reason": "quiescence_gate_failed",
            "candidate_wall_s": round(time.time() - candidate_started, 3),
        }
        result["failure_evidence"] = failure_evidence
        result["notes"] = candidate_notes(candidate, early_reject, skipped_c4=False)
        return result

    warmup_res = run_request_stage(
        chat_url=chat_url,
        payload=payload,
        concurrency=1,
        requests_per_stage=warmup_requests,
        request_timeout_s=request_timeout_s,
        stage_timeout_s=int(budgets.get("stage_timeout_s", 600)),
    )
    result["warmup"] = {
        **warmup_res,
        "discarded": True,
    }
    if not warmup_res.get("passed"):
        failure_evidence = capture_failure_evidence(studio_host, log_path, monitor_ports)
        classification = classify_host_from_ready_and_evidence(ready_res, failure_evidence)
        result["host_state"] = classification["host_state"]
        result["ssh_error_class"] = classification["ssh_error_class"]
        result["summary"] = {
            "failure_reason": "warmup_failed",
            "candidate_wall_s": round(time.time() - candidate_started, 3),
        }
        result["failure_evidence"] = failure_evidence
        result["notes"] = candidate_notes(candidate, early_reject, skipped_c4=False)
        return result

    skipped_c4 = False
    measured_latencies: List[float] = []
    total_tokens = 0
    total_stage_wall = 0.0
    peak_running = None
    peak_waiting = None
    peak_kv = None
    fail_reason = None

    for concurrency in concurrency_sweep:
        if early_reject and concurrency >= 4:
            skipped_c4 = True
            result["stages"].append(
                {
                    "name": f"c{concurrency}",
                    "concurrency": concurrency,
                    "skipped": True,
                    "reason": "early_reject_low_startup_max_concurrency",
                }
            )
            continue

        if time.time() - candidate_started > float(budgets.get("candidate_timeout_s", 1800)):
            fail_reason = "candidate_timeout_budget_exceeded"
            break

        poller = MetricsPoller(
            metrics_url=metrics_url,
            poll_interval_s=float(request_shape.get("metrics_poll_interval_s", 1.0)),
            timeout_s=10,
            running_names=metrics_names["running"],
            waiting_names=metrics_names["waiting"],
            kv_names=metrics_names["kv_usage_perc"],
        )
        poller.start()
        stage = run_request_stage(
            chat_url=chat_url,
            payload=payload,
            concurrency=concurrency,
            requests_per_stage=requests_per_stage,
            request_timeout_s=request_timeout_s,
            stage_timeout_s=int(budgets.get("stage_timeout_s", 600)),
        )
        poller.stop()
        poller.join(timeout=3)
        metrics_summary = poller.summary()
        stage["metrics_summary"] = metrics_summary
        stage["skipped"] = False
        stage["name"] = f"c{concurrency}"
        stage["optional_ttft_itl_hist"] = None
        result["stages"].append(stage)

        stage_latencies = [
            float(x["latency_s"]) for x in stage.get("raw_results", []) if x.get("latency_s") is not None
        ]
        measured_latencies.extend(stage_latencies)
        total_tokens += int(stage.get("completion_tokens_total") or 0)
        total_stage_wall += float(stage.get("stage_wall_s") or 0.0)

        pr = metrics_summary.get("peak_running")
        pw = metrics_summary.get("peak_waiting")
        pk = metrics_summary.get("peak_kv_usage_perc")
        if pr is not None:
            peak_running = pr if peak_running is None else max(float(peak_running), float(pr))
        if pw is not None:
            peak_waiting = pw if peak_waiting is None else max(float(peak_waiting), float(pw))
        if pk is not None:
            peak_kv = pk if peak_kv is None else max(float(peak_kv), float(pk))

        if not stage.get("passed"):
            fail_reason = f"stage_failed_c{concurrency}"
            break

        alive = http_get_status(health_url, timeout_s=10)
        if alive.get("status") != 200:
            fail_reason = "lane_health_failed_post_stage"
            break

    p95_c4 = None
    for stage in result["stages"]:
        if stage.get("concurrency") == 4 and not stage.get("skipped"):
            p95_c4 = stage.get("p95_latency_s")
            break

    result["summary"] = {
        "failure_reason": fail_reason,
        "candidate_wall_s": round(time.time() - candidate_started, 3),
        "client_latency_p50_s": percentile(measured_latencies, 50),
        "client_latency_p95_s": percentile(measured_latencies, 95),
        "client_tokens_per_sec": round(total_tokens / total_stage_wall, 4) if total_stage_wall > 0 else 0.0,
        "completion_tokens_total": total_tokens,
        "peak_running": peak_running,
        "peak_waiting": peak_waiting,
        "peak_kv_usage_perc": peak_kv,
        "p95_latency_s_at_c4": p95_c4,
    }

    passed = fail_reason is None
    result["pass_fail"] = "PASS" if passed else "FAIL"
    if not passed:
        failure_evidence = capture_failure_evidence(studio_host, log_path, monitor_ports)
        classification = classify_host_from_ready_and_evidence(ready_res, failure_evidence)
        result["host_state"] = classification["host_state"]
        result["ssh_error_class"] = classification["ssh_error_class"]
        result["failure_evidence"] = failure_evidence
    result["notes"] = candidate_notes(candidate, early_reject, skipped_c4=skipped_c4)
    return result


def main() -> int:
    args = parse_args()
    profile_path = Path(args.profile).resolve()
    out_path = Path(args.out).resolve()
    out_md = out_path.with_suffix(".md")

    profile = load_profile(profile_path)
    lane = profile["lane"]
    request_shape = profile["fixed_request_shape"]
    metrics_names = profile.get(
        "metric_names",
        {
            "running": ["vllm:num_requests_running", "vllm_num_requests_running"],
            "waiting": ["vllm:num_requests_waiting", "vllm_num_requests_waiting"],
            "kv_usage_perc": ["vllm:kv_cache_usage_perc", "vllm_kv_cache_usage_perc"],
        },
    )
    budgets = profile.get("budgets", {})
    monitor_ports = [int(p) for p in profile.get("monitor_ports", [8120, 8121, 8122])]

    candidates: List[Candidate] = []
    if args.mode in ("phaseA", "all"):
        candidates.extend(build_phase_a_candidates(profile))
    if args.mode in ("phaseB", "all"):
        candidates.extend(build_phase_b_candidates(profile))

    report: Dict[str, Any] = {
        "generated_at": utc_now(),
        "host": socket.gethostname(),
        "profile": str(profile_path),
        "mode": args.mode,
        "lane": {
            "name": lane.get("name"),
            "port": lane.get("port"),
            "chat_url": lane.get("chat_url"),
            "metrics_url": lane.get("metrics_url"),
            "health_url": lane.get("health_url"),
            "models_url": lane.get("models_url"),
        },
        "fixed_request_shape": request_shape,
        "candidates_total": len(candidates),
        "candidate_results": [],
        "ranked_candidates": [],
        "winner": None,
        "notes": [],
    }

    if not candidates:
        report["notes"].append("No candidates generated for selected mode.")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2) + "\n")
        write_markdown_summary(report, out_md)
        print(json.dumps({"report_path": str(out_path), "markdown_path": str(out_md), "winner": None}))
        return 1

    for candidate in candidates:
        result = execute_candidate(
            candidate=candidate,
            profile=profile,
            lane=lane,
            metrics_names=metrics_names,
            request_shape=request_shape,
            budgets=budgets,
            monitor_ports=monitor_ports,
        )
        report["candidate_results"].append(result)

    ranked = rank_candidates(report["candidate_results"])
    report["ranked_candidates"] = ranked
    winner = next((c["candidate_id"] for c in ranked if c.get("pass_fail") == "PASS"), None)
    report["winner"] = winner

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    write_markdown_summary(report, out_md)

    print(
        json.dumps(
            {
                "report_path": str(out_path),
                "markdown_path": str(out_md),
                "winner": winner,
                "candidates_total": len(report["candidate_results"]),
                "passed": sum(1 for c in report["candidate_results"] if c.get("pass_fail") == "PASS"),
            }
        )
    )
    return 0 if winner else 1


if __name__ == "__main__":
    raise SystemExit(main())
