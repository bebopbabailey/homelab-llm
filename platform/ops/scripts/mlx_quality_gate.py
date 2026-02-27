#!/usr/bin/env python3
"""
Lightweight inference quality gate for Studio MLX lanes.

Checks:
- /v1/models is reachable per lane
- a short completion/chat request succeeds
- output is non-empty
- output does not contain protocol leakage markers
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_FIXTURE = (
    "/home/christopherbailey/homelab-llm/layer-inference/docs/fixtures/inference_golden_smoke.json"
)
DEFAULT_PORTS = "8100,8101,8102"
DEFAULT_HOST = "127.0.0.1"
LANE_BY_PORT = {8100: "deep", 8101: "main", 8102: "fast"}


def _http_json(url: str, method: str = "GET", payload=None, timeout: int = 30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body or "{}")


def _extract_text(response_obj: dict):
    choices = response_obj.get("choices") or []
    if not choices:
        return ""
    first = choices[0] or {}
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    text = first.get("text")
    if isinstance(text, str):
        return text
    return ""


def _run_case(host: str, port: int, case: dict, defaults: dict):
    lane = case["lane"]
    timeout = int(case.get("request_timeout_s", defaults.get("request_timeout_s", 45)))
    max_tokens = int(case.get("max_tokens", defaults.get("max_tokens", 64)))
    endpoint = case.get("endpoint", defaults.get("endpoint", "chat.completions"))
    forbidden = list(defaults.get("forbidden_substrings", [])) + list(case.get("forbidden_substrings", []))
    required = list(case.get("required_substrings", []))

    result = {
        "lane": lane,
        "port": port,
        "ok": False,
        "status": "unknown",
        "model_id": None,
        "output_preview": "",
        "errors": [],
    }

    base = f"http://{host}:{port}"
    try:
        models_obj = _http_json(f"{base}/v1/models", timeout=timeout)
        model_id = (models_obj.get("data") or [{}])[0].get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            result["status"] = "fail"
            result["errors"].append("missing model id from /v1/models")
            return result
        result["model_id"] = model_id
    except Exception as exc:
        result["status"] = "fail"
        result["errors"].append(f"/v1/models failed: {exc}")
        return result

    prompt = case["prompt"]
    try:
        if endpoint == "completions":
            payload = {"model": result["model_id"], "prompt": prompt, "max_tokens": max_tokens}
            response_obj = _http_json(f"{base}/v1/completions", method="POST", payload=payload, timeout=timeout)
        else:
            payload = {
                "model": result["model_id"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }
            response_obj = _http_json(
                f"{base}/v1/chat/completions", method="POST", payload=payload, timeout=timeout
            )
    except urllib.error.HTTPError as exc:
        result["status"] = "fail"
        result["errors"].append(f"completion endpoint failed: HTTP {exc.code}")
        return result
    except Exception as exc:
        result["status"] = "fail"
        result["errors"].append(f"completion endpoint failed: {exc}")
        return result

    text = _extract_text(response_obj).strip()
    result["output_preview"] = text[:180]

    if not text:
        result["status"] = "fail"
        result["errors"].append("empty output")
        return result

    lowered = text.lower()
    for token in forbidden:
        if token and token.lower() in lowered:
            result["errors"].append(f"forbidden marker detected: {token}")
    for token in required:
        if token and token.lower() not in lowered:
            result["errors"].append(f"required marker missing: {token}")

    if result["errors"]:
        result["status"] = "fail"
        return result

    result["ok"] = True
    result["status"] = "pass"
    return result


def _parse_ports(raw: str):
    ports = []
    for item in (raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        ports.append(int(item))
    if not ports:
        raise ValueError("no ports specified")
    return ports


def main():
    parser = argparse.ArgumentParser(description="Quality gate for Studio MLX lanes.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Target host (default: 127.0.0.1)")
    parser.add_argument("--ports", default=DEFAULT_PORTS, help="Comma-separated ports (default: 8100,8101,8102)")
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE, help="Fixture JSON path")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        raise SystemExit(f"fixture not found: {fixture_path}")
    fixture = json.loads(fixture_path.read_text() or "{}")
    defaults = fixture.get("defaults") or {}
    cases = fixture.get("cases") or []

    if not cases:
        raise SystemExit("fixture has no cases")

    ports = _parse_ports(args.ports)
    lane_port = {LANE_BY_PORT.get(port, f"lane-{port}"): port for port in ports}

    results = []
    for case in cases:
        lane = case.get("lane")
        if lane not in lane_port:
            continue
        port = lane_port[lane]
        results.append(_run_case(args.host, port, case, defaults))

    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    summary = {"host": args.host, "ports": ports, "total": total, "passed": passed, "failed": failed, "results": results}

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("lane\tport\tstatus\tmodel_id\tpreview")
        for row in results:
            print(
                f"{row['lane']}\t{row['port']}\t{row['status']}\t{row.get('model_id') or '-'}\t{row.get('output_preview') or '-'}"
            )
            for err in row["errors"]:
                print(f"  - {err}")
        print(f"\nsummary: passed={passed} failed={failed} total={total}")

    raise SystemExit(0 if failed == 0 and total > 0 else 1)


if __name__ == "__main__":
    main()
