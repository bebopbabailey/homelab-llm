#!/usr/bin/env python3
"""Measure time-to-first-token (TTFT) and total time for streaming responses."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request


def _make_request(url: str, payload: dict, bearer: str | None) -> urllib.request.Request:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")
    return req


def main() -> int:
    parser = argparse.ArgumentParser(description="Stream benchmark (TTFT + total time)")
    parser.add_argument("--url", default=os.environ.get("LITELLM_API_BASE", "http://127.0.0.1:4000/v1/chat/completions"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--bearer", default=os.environ.get("LITELLM_PROXY_KEY"))
    args = parser.parse_args()

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": args.max_tokens,
        "stream": True,
    }

    req = _make_request(args.url, payload, args.bearer)
    start = time.time()
    first_token = None
    total_bytes = 0

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw in resp:
                total_bytes += len(raw)
                line = raw.strip()
                if not line:
                    continue
                if line.startswith(b"data: "):
                    data = line[6:]
                    if data == b"[DONE]":
                        break
                    if first_token is None:
                        first_token = time.time()
        end = time.time()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    ttft = (first_token - start) if first_token else None
    total = end - start

    print(f"ttft_seconds={ttft:.3f}" if ttft is not None else "ttft_seconds=NA")
    print(f"total_seconds={total:.3f}")
    print(f"bytes={total_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
