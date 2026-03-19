#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from subprocess import CompletedProcess, run


@dataclass(frozen=True)
class LoadSpec:
    model: str
    identifier: str
    context_length: int
    parallel: int


def parse_load_spec(raw: str) -> LoadSpec:
    parts = raw.split("|")
    if len(parts) != 4:
        raise ValueError(f"invalid load spec: {raw!r}")
    model, identifier, context_length, parallel = parts
    return LoadSpec(
        model=model.strip(),
        identifier=identifier.strip(),
        context_length=int(context_length),
        parallel=int(parallel),
    )


def run_checked(cmd: list[str], *, allow_failure: bool = False) -> CompletedProcess[str]:
    proc = run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0 and not allow_failure:
        raise RuntimeError(
            "command failed: {}\nstdout={}\nstderr={}".format(
                " ".join(cmd), proc.stdout.strip(), proc.stderr.strip()
            )
        )
    return proc


def wait_for_models(base_url: str, api_key: str | None, timeout_s: float, poll_s: float) -> dict:
    deadline = time.time() + timeout_s
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    while time.time() < deadline:
        req = urllib.request.Request(f"{base_url}/models", headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=min(10.0, poll_s + 5.0)) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode())
        except urllib.error.HTTPError:
            pass
        except urllib.error.URLError:
            pass
        time.sleep(poll_s)
    raise RuntimeError(f"timed out waiting for {base_url}/models")


def ensure_identifier_loaded(base_url: str, api_key: str | None, identifier: str, timeout_s: float, poll_s: float) -> None:
    deadline = time.time() + timeout_s
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    while time.time() < deadline:
        req = urllib.request.Request(f"{base_url}/models", headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=min(10.0, poll_s + 5.0)) as resp:
                if resp.status != 200:
                    time.sleep(poll_s)
                    continue
                body = json.loads(resp.read().decode())
                data = body.get("data", [])
                if any((item or {}).get("id") == identifier for item in data if isinstance(item, dict)):
                    return
        except Exception:
            pass
        time.sleep(poll_s)
    raise RuntimeError(f"timed out waiting for model identifier {identifier!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Thin daemon-aware LM Studio bootstrap for canonical llmster lanes.")
    parser.add_argument("--lms-bin", required=True, help="Pinned versioned lms binary path.")
    parser.add_argument("--bind", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--api-key-env", default="")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--startup-timeout", type=float, default=90.0)
    parser.add_argument(
        "--load-spec",
        action="append",
        default=[],
        help="model|identifier|context_length|parallel",
    )
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    load_specs = [parse_load_spec(spec) for spec in args.load_spec]
    base_url = f"http://{args.bind}:{args.port}/v1"

    run_checked([args.lms_bin, "daemon", "up"])
    run_checked([args.lms_bin, "daemon", "status"])

    # `lms server start` may return non-zero if the server is already running on
    # the target bind/port. The health check below is the actual success gate.
    run_checked(
        [args.lms_bin, "server", "start", "--bind", args.bind, "--port", str(args.port)],
        allow_failure=True,
    )
    wait_for_models(base_url, api_key, args.startup_timeout, args.poll_interval)

    for spec in load_specs:
        run_checked(
            [
                args.lms_bin,
                "load",
                spec.model,
                "--identifier",
                spec.identifier,
                "--context-length",
                str(spec.context_length),
                "--parallel",
                str(spec.parallel),
                "-y",
            ]
        )
        ensure_identifier_loaded(base_url, api_key, spec.identifier, args.startup_timeout, args.poll_interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
