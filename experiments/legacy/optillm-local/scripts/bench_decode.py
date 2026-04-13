#!/usr/bin/env python3
"""Benchmark default vs entropy decoding in an isolated MLX-LM experiment."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_PROMPTS = [
    "Summarize in 3 bullet points why temperature affects generation diversity.",
    "Give a concise troubleshooting checklist for intermittent API timeout spikes.",
    "Write a short migration risk matrix for rolling out a new inference backend.",
    "Explain the tradeoff between latency and best-of-N quality in one paragraph.",
    "List 5 objective metrics to compare two decoding strategies.",
]


@dataclass
class RunResult:
    mode: str
    status: int
    latency_seconds: float
    completion_tokens: int
    had_metadata: bool
    error: Optional[str] = None


def post_json(url: str, payload: Dict[str, Any], bearer: str | None, timeout: int) -> tuple[int, Dict[str, Any], float]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body), time.time() - start
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(body) if body else {"error": body}
        except json.JSONDecodeError:
            parsed = {"error": body}
        return exc.code, parsed, time.time() - start
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc)}, time.time() - start
    except Exception as exc:  # pragma: no cover - defensive fallback
        return 0, {"error": str(exc)}, time.time() - start


def build_payload(mode: str, model: str, prompt: str, max_tokens: int) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
        "temperature": 0.7,
    }
    if mode == "default":
        return base

    if mode == "entropy":
        return {
            **base,
            "decoding": "entropy_decoding",
            "return_decoding_metadata": True,
            "entropy_target": 2.6,
            "entropy_alpha": 0.35,
            "entropy_temp_min": 0.2,
            "entropy_temp_max": 1.1,
            "top_k": 40,
            "min_p": 0.03,
        }

    raise ValueError(f"unsupported mode: {mode}")


def run_single(url: str, bearer: str | None, timeout: int, payload: Dict[str, Any], mode: str) -> RunResult:
    status, response, latency = post_json(url, payload, bearer, timeout)
    usage = response.get("usage") or {}
    completion_tokens = int(usage.get("completion_tokens") or 0)
    return RunResult(
        mode=mode,
        status=status,
        latency_seconds=latency,
        completion_tokens=completion_tokens,
        had_metadata="decoding_metadata" in response,
        error=None if status == 200 else str(response.get("error", response)),
    )


def classify_failure(result: RunResult) -> str:
    if result.status == 0:
        error_text = (result.error or "").lower()
        if "timed out" in error_text:
            return "timeout"
        return "network_or_client"
    if result.status >= 500:
        return "http_5xx"
    if result.status >= 400:
        return "http_4xx"
    return "unknown"


def summarize(values: Iterable[float]) -> Dict[str, float]:
    numbers = list(values)
    if not numbers:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}

    ordered = sorted(numbers)
    return {
        "count": len(numbers),
        "mean": round(statistics.fmean(numbers), 4),
        "p50": round(percentile(ordered, 50.0), 4),
        "p95": round(percentile(ordered, 95.0), 4),
        "max": round(max(numbers), 4),
    }


def percentile(sorted_values: List[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    idx = (p / 100.0) * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def load_prompts(path: Optional[str]) -> List[str]:
    if not path:
        return DEFAULT_PROMPTS

    lines = []
    for raw in Path(path).read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("{"):
            data = json.loads(raw)
            lines.append(data.get("prompt", ""))
        else:
            lines.append(raw)

    return [line for line in lines if line]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark default vs entropy decoding")
    parser.add_argument("--url", default=os.environ.get("MLX_EXPERIMENTAL_URL", "http://127.0.0.1:8130/v1/chat/completions"))
    parser.add_argument("--model", default="main")
    parser.add_argument("--prompts", help="Optional txt/jsonl prompt file")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bearer", default=os.environ.get("LITELLM_MASTER_KEY") or os.environ.get("OPTILLM_API_KEY"))
    parser.add_argument("--json-out", help="Optional output path")
    args = parser.parse_args()

    if args.repeats <= 0:
        raise SystemExit("--repeats must be >= 1")
    if args.concurrency <= 0:
        raise SystemExit("--concurrency must be >= 1")

    prompts = load_prompts(args.prompts)
    random.Random(args.seed).shuffle(prompts)

    summary: Dict[str, Any] = {
        "url": args.url,
        "model": args.model,
        "repeats": args.repeats,
        "concurrency": args.concurrency,
        "prompt_count": len(prompts),
        "wall_seconds": 0.0,
        "modes": {},
    }

    total_wall_seconds = 0.0
    any_failure = False

    for mode in ("default", "entropy"):
        jobs: list[Dict[str, Any]] = []
        for prompt in prompts:
            for _ in range(args.repeats):
                jobs.append(build_payload(mode, args.model, prompt, args.max_tokens))

        mode_started = time.time()
        mode_results: list[RunResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [
                pool.submit(run_single, args.url, args.bearer, args.timeout, payload, mode)
                for payload in jobs
            ]
            for future in concurrent.futures.as_completed(futures):
                mode_results.append(future.result())
        mode_ended = time.time()
        mode_wall = max(mode_ended - mode_started, 1e-9)
        total_wall_seconds += mode_wall

        successes = [r for r in mode_results if r.status == 200]
        failures = [r for r in mode_results if r.status != 200]
        any_failure = any_failure or bool(failures)

        completion_tokens_total = sum(r.completion_tokens for r in successes)
        failure_breakdown: Dict[str, int] = {}
        for failure in failures:
            bucket = classify_failure(failure)
            failure_breakdown[bucket] = failure_breakdown.get(bucket, 0) + 1

        summary["modes"][mode] = {
            "requests": len(mode_results),
            "success": len(successes),
            "failure": len(failures),
            "error_rate_pct": round((len(failures) / len(mode_results) * 100.0) if mode_results else 0.0, 4),
            "latency_seconds": summarize(r.latency_seconds for r in successes),
            "completion_tokens": summarize(r.completion_tokens for r in successes),
            "completion_tokens_total": completion_tokens_total,
            "requests_per_second": round(len(mode_results) / mode_wall, 4),
            "completion_tokens_per_second": round(completion_tokens_total / mode_wall, 4),
            "mode_wall_seconds": round(mode_wall, 4),
            "metadata_rate": round(
                (sum(1 for r in successes if r.had_metadata) / len(successes)) if successes else 0.0,
                4,
            ),
            "failure_breakdown": failure_breakdown,
            "sample_errors": [r.error for r in failures[:3]],
        }

    summary["wall_seconds"] = round(total_wall_seconds, 3)

    output = json.dumps(summary, indent=2)
    print(output)

    if args.json_out:
        Path(args.json_out).write_text(output + "\n")

    return 0 if not any_failure else 1


if __name__ == "__main__":
    raise SystemExit(main())
