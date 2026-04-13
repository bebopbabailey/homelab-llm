#!/usr/bin/env python3
"""Run benchmark matrix (models x concurrency) for OptiLLM-on-MLX experiments."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_URL = "http://127.0.0.1:8130/v1/chat/completions"
DEFAULT_MODELS = ["main", "gpt-oss-20b", "gpt-oss-120b"]
DEFAULT_CONCURRENCY = [1, 4, 8]
DEFAULT_REPEATS = 3
DEFAULT_MAX_TOKENS = 256
DEFAULT_TIMEOUT = 240
DEFAULT_OUTPUT_DIR = "/tmp"


def parse_csv(text: str) -> List[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


def parse_csv_int(text: str) -> List[int]:
    return [int(x) for x in parse_csv(text)]


def load_gate_profile(path: str | None) -> Dict[str, Any]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, dict):
        raise ValueError("gate config must be a JSON object")
    return payload.get("viability_gate", payload)


def run_cmd(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run benchmark matrix for OptiLLM-on-MLX")
    parser.add_argument("--gate-config", help="Optional viability gate config JSON")
    parser.add_argument("--url", default=None)
    parser.add_argument("--models", default=None, help="Comma list, e.g. main,gpt-oss-20b")
    parser.add_argument("--concurrency-values", default=None, help="Comma list, e.g. 1,4,8")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--prompts", help="Optional txt/jsonl prompt file")
    parser.add_argument("--bearer")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    profile = load_gate_profile(args.gate_config)

    url = args.url or profile.get("url") or DEFAULT_URL

    if args.models:
        models = parse_csv(args.models)
    elif isinstance(profile.get("models"), list):
        models = [str(x) for x in profile["models"]]
    else:
        models = list(DEFAULT_MODELS)

    if args.concurrency_values:
        concurrencies = parse_csv_int(args.concurrency_values)
    elif isinstance(profile.get("concurrency_values"), list):
        concurrencies = [int(x) for x in profile["concurrency_values"]]
    else:
        concurrencies = list(DEFAULT_CONCURRENCY)

    repeats = int(args.repeats if args.repeats is not None else profile.get("repeats", DEFAULT_REPEATS))
    max_tokens = int(args.max_tokens if args.max_tokens is not None else profile.get("max_tokens", DEFAULT_MAX_TOKENS))
    timeout = int(args.timeout if args.timeout is not None else profile.get("bench_timeout", DEFAULT_TIMEOUT))
    output_dir = Path(args.output_dir or profile.get("output_dir") or DEFAULT_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    prompts = args.prompts if args.prompts else profile.get("prompts")

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / f"optillm_mlx_matrix_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    bench_script = script_dir / "bench_decode.py"

    matrix: Dict[str, Any] = {
        "generated_at": timestamp,
        "url": url,
        "models": models,
        "concurrency_values": concurrencies,
        "repeats": repeats,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "results": {},
    }

    failures = 0
    for model in models:
        matrix["results"][model] = {}
        for concurrency in concurrencies:
            artifact = run_dir / f"bench_{model.replace('/', '_')}_c{concurrency}.json"
            cmd = [
                sys.executable,
                str(bench_script),
                "--url",
                url,
                "--model",
                model,
                "--repeats",
                str(repeats),
                "--max-tokens",
                str(max_tokens),
                "--timeout",
                str(timeout),
                "--concurrency",
                str(concurrency),
                "--json-out",
                str(artifact),
            ]
            if prompts:
                cmd += ["--prompts", str(prompts)]
            if args.bearer:
                cmd += ["--bearer", args.bearer]

            completed = run_cmd(cmd)
            if completed.returncode != 0:
                failures += 1

            matrix["results"][model][str(concurrency)] = {
                "returncode": completed.returncode,
                "artifact": str(artifact),
                "command": cmd,
                "stderr_preview": completed.stderr.splitlines()[:5],
            }

    out_path = run_dir / "matrix_summary.json"
    out_path.write_text(json.dumps(matrix, indent=2) + "\n")

    print(json.dumps({
        "matrix_summary": str(out_path),
        "failure_jobs": failures,
    }, indent=2))

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
