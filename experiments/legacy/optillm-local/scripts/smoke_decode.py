#!/usr/bin/env python3
"""Direct smoke test for default vs entropy decoding on an MLX-LM endpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


def post_json(url: str, payload: Dict[str, Any], bearer: str | None, timeout: int) -> Tuple[int, Dict[str, Any], float]:
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


def extract_text(response: Dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test decode-time controls")
    parser.add_argument("--url", default=os.environ.get("MLX_EXPERIMENTAL_URL", "http://127.0.0.1:8130/v1/chat/completions"))
    parser.add_argument("--model", default="main")
    parser.add_argument("--prompt", default="Explain briefly why entropy can be useful during decoding.")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--bearer", default=os.environ.get("LITELLM_MASTER_KEY") or os.environ.get("OPTILLM_API_KEY"))
    parser.add_argument("--expect-metadata", action="store_true")
    args = parser.parse_args()

    base = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": args.max_tokens,
        "stream": False,
        "temperature": 0.7,
    }

    baseline = dict(base)
    entropy = {
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

    rows = []
    for name, payload in (("default", baseline), ("entropy", entropy)):
        status, response, latency = post_json(args.url, payload, args.bearer, args.timeout)
        row = {
            "mode": name,
            "status": status,
            "latency_seconds": round(latency, 3),
            "text_preview": extract_text(response)[:140],
            "has_decoding_metadata": "decoding_metadata" in response,
        }
        if status != 200:
            row["error"] = response.get("error", response)
        if "decoding_metadata" in response:
            row["decoding_metadata"] = response["decoding_metadata"]
        rows.append(row)

    print(json.dumps({"url": args.url, "model": args.model, "results": rows}, indent=2))

    failures = [row for row in rows if row["status"] != 200]
    if failures:
        return 1

    if args.expect_metadata and not rows[1].get("has_decoding_metadata"):
        print("entropy response did not include decoding_metadata", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
