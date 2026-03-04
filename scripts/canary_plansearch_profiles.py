#!/usr/bin/env python3
"""Run a repeatable A/B canary for boost-plan vs boost-plan-trio."""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


TRUNCATION_MARKER = "Response was truncated due to token limit"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def _read_prompts(path: Path) -> list[str]:
    prompts: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        prompts.append(line)
    if not prompts:
        raise RuntimeError(f"Prompt file has no usable prompts: {path}")
    return prompts


def _extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = (choices[0].get("message") or {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                value = item.get("text") or item.get("output_text") or ""
                if isinstance(value, str):
                    text_parts.append(value)
        return "".join(text_parts)
    return ""


def _is_truncated(payload: dict[str, Any], content: str) -> bool:
    if TRUNCATION_MARKER in content:
        return True
    choices = payload.get("choices") or []
    if not choices:
        return False
    finish_reason = choices[0].get("finish_reason") if isinstance(choices[0], dict) else None
    return finish_reason == "length"


def _one_call(
    url: str,
    bearer: str | None,
    model: str,
    prompt: str,
    max_tokens: int,
) -> tuple[dict[str, Any], float]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")

    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=240) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    elapsed = time.perf_counter() - start
    return payload, elapsed


def _run_profile(
    *,
    url: str,
    bearer: str | None,
    model: str,
    prompts: list[str],
    max_tokens: int,
) -> dict[str, Any]:
    latencies: list[float] = []
    chars: list[int] = []
    empty = 0
    trunc = 0
    errors = 0

    for idx, prompt in enumerate(prompts, start=1):
        try:
            payload, elapsed = _one_call(url, bearer, model, prompt, max_tokens)
            content = _extract_content(payload).strip()
            latencies.append(elapsed)
            chars.append(len(content))
            if not content:
                empty += 1
            if _is_truncated(payload, content):
                trunc += 1
            print(f"[{model}] {idx}/{len(prompts)} ok latency={elapsed:.3f}s chars={len(content)}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            errors += 1
            print(f"[{model}] {idx}/{len(prompts)} error: {exc}", file=sys.stderr)

    p50 = _percentile(latencies, 0.50)
    p95 = _percentile(latencies, 0.95)
    avg_chars = statistics.fmean(chars) if chars else 0.0

    return {
        "model": model,
        "runs": len(prompts),
        "ok": len(prompts) - errors,
        "errors": errors,
        "empty": empty,
        "trunc": trunc,
        "p50_seconds": round(p50, 4),
        "p95_seconds": round(p95, 4),
        "avg_chars": round(avg_chars, 1),
    }


def _default_prompt_file() -> Path:
    return Path(__file__).resolve().with_name("canary_prompts_plansearch.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="PlanSearch canary A/B runner")
    parser.add_argument("--url", default=os.environ.get("LITELLM_API_BASE", "http://127.0.0.1:4000/v1") + "/chat/completions")
    parser.add_argument("--bearer", default=os.environ.get("LITELLM_API_KEY") or os.environ.get("LITELLM_PROXY_KEY"))
    parser.add_argument("--model-a", default="boost-plan")
    parser.add_argument("--model-b", default="boost-plan-trio")
    parser.add_argument("--max-tokens", type=int, default=160)
    parser.add_argument("--prompts", type=Path, default=_default_prompt_file())
    parser.add_argument("--p95-ratio-max", type=float, default=1.75)
    parser.add_argument("--allow-empty", action="store_true", help="Do not fail gate on empty outputs")
    parser.add_argument("--out-json", type=Path, default=None)
    args = parser.parse_args()

    prompts = _read_prompts(args.prompts)
    baseline = _run_profile(
        url=args.url,
        bearer=args.bearer,
        model=args.model_a,
        prompts=prompts,
        max_tokens=args.max_tokens,
    )
    candidate = _run_profile(
        url=args.url,
        bearer=args.bearer,
        model=args.model_b,
        prompts=prompts,
        max_tokens=args.max_tokens,
    )

    baseline_p95 = baseline["p95_seconds"] or 1e-9
    ratio = float(candidate["p95_seconds"]) / float(baseline_p95)
    gate_empty_pass = args.allow_empty or int(candidate["empty"]) == 0
    gate_latency_pass = ratio <= args.p95_ratio_max

    summary = {
        "baseline": baseline,
        "candidate": candidate,
        "gate": {
            "require_zero_empty": not args.allow_empty,
            "empty_pass": gate_empty_pass,
            "p95_ratio": round(ratio, 4),
            "p95_ratio_max": args.p95_ratio_max,
            "latency_pass": gate_latency_pass,
            "pass": gate_empty_pass and gate_latency_pass,
        },
    }

    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.out_json:
        args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 0 if summary["gate"]["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
