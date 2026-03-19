#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


def _post(url: str, payload: dict, api_key: str | None, timeout: float) -> tuple[int, dict, float]:
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body, time.perf_counter() - start
    except urllib.error.HTTPError as exc:
        body = exc.read().decode() if exc.fp else ""
        return exc.code, {"error": body}, time.perf_counter() - start


def _object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _single_tool_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "noop",
            "description": "Accept a short value and echo it back through a tool call.",
            "parameters": _object_schema(
                {
                    "value": {
                        "type": "string",
                        "description": "A short tag string to prove argument formatting.",
                    }
                },
                ["value"],
            ),
        },
    }


def _large_tool_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "compose_summary",
            "description": "Return a structured summary payload with short required fields only.",
            "parameters": _object_schema(
                {
                    "title": {"type": "string", "description": "Short title."},
                    "status": {
                        "type": "string",
                        "description": "One of draft, review, or final.",
                        "enum": ["draft", "review", "final"],
                    },
                    "priority": {
                        "type": "string",
                        "description": "One of low, medium, or high.",
                        "enum": ["low", "medium", "high"],
                    },
                    "summary": {"type": "string", "description": "One-sentence summary."},
                    "owner": {
                        "type": "object",
                        "description": "Named owner object.",
                        "properties": {
                            "name": {"type": "string", "description": "Owner name."},
                            "team": {"type": "string", "description": "Owner team."},
                        },
                        "required": ["name", "team"],
                        "additionalProperties": False,
                    },
                },
                ["title", "status", "priority", "summary", "owner"],
            ),
        },
    }


def _response_format_schema(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": True,
        },
    }


def _extract_responses_text(body: dict[str, Any]) -> str:
    if isinstance(body.get("output_text"), str):
        return body["output_text"]

    output = body.get("output")
    if not isinstance(output, list):
        return ""

    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "".join(chunks)


def _expect_text(content: str) -> Callable[[dict], bool]:
    def check(body: dict) -> bool:
        message = body["choices"][0]["message"]["content"]
        return isinstance(message, str) and content in message

    return check


def _expect_json_keys(required_keys: list[str]) -> Callable[[dict], bool]:
    def check(body: dict) -> bool:
        message = body["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(message)
        except Exception:
            return False
        return all(key in parsed for key in required_keys)

    return check


def _expect_tool_call(tool_name: str, required_arg: str | None = None) -> Callable[[dict], bool]:
    def check(body: dict) -> bool:
        message = body["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return False
        fn = tool_calls[0].get("function") or {}
        if fn.get("name") != tool_name:
            return False
        try:
            parsed = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            return False
        if required_arg and not isinstance(parsed.get(required_arg), str):
            return False
        return True

    return check


def _expect_responses_text(content: str) -> Callable[[dict], bool]:
    def check(body: dict) -> bool:
        return content in _extract_responses_text(body)

    return check


def _run_case(
    url: str,
    payload: dict,
    checker: Callable[[dict], bool],
    attempts: int,
    timeout: float,
    api_key: str | None,
) -> dict[str, Any]:
    successes = 0
    latencies = []
    failures = []
    for _ in range(attempts):
        status, body, latency = _post(url, payload, api_key, timeout)
        latencies.append(latency)
        if status == 200 and checker(body):
            successes += 1
        else:
            failures.append({"status": status, "body": body})
    ordered = sorted(latencies)
    return {
        "attempts": attempts,
        "successes": successes,
        "p50_latency_s": statistics.median(ordered) if ordered else None,
        "p95_latency_s": ordered[max(0, int(len(ordered) * 0.95) - 1)] if ordered else None,
        "failures": failures[:3],
    }


def _run_concurrency(
    url: str,
    payload: dict,
    concurrency: int,
    requests: int,
    timeout: float,
    api_key: str | None,
) -> dict[str, Any]:
    latencies = []
    statuses = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_post, url, payload, api_key, timeout) for _ in range(requests)]
        for future in futures:
            status, _body, latency = future.result()
            latencies.append(latency)
            statuses.append(status)
    ordered = sorted(latencies)
    return {
        "concurrency": concurrency,
        "requests": requests,
        "ok": all(status == 200 for status in statuses),
        "p50_latency_s": statistics.median(ordered) if ordered else None,
        "p95_latency_s": ordered[max(0, int(len(ordered) * 0.95) - 1)] if ordered else None,
        "status_counts": {str(status): statuses.count(status) for status in sorted(set(statuses))},
    }


def _chat_payload(model: str, prompt: str, *, max_tokens: int = 256) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": max_tokens,
        "reasoning_effort": "low",
    }


def _response_payload(model: str, prompt: str, *, max_output_tokens: int = 256) -> dict[str, Any]:
    return {
        "model": model,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": "low"},
    }


def _profile_defaults(profile: str, model: str) -> tuple[int, int]:
    if profile == "deep":
        return 2, 4
    if profile == "fast":
        return 4, 8
    if "120b" in model.lower():
        return 2, 4
    return 4, 8


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GPT-OSS acceptance checks against one OpenAI-compatible endpoint.")
    parser.add_argument("--base-url", required=True, help="Base URL ending in /v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--profile", choices=["auto", "fast", "deep"], default="auto")
    args = parser.parse_args()

    chat_url = args.base_url.rstrip("/") + "/chat/completions"
    responses_url = args.base_url.rstrip("/") + "/responses"
    tool_schema = _single_tool_schema()
    large_tool_schema = _large_tool_schema()
    concurrency, requests = _profile_defaults(args.profile, args.model)

    results = {
        "plain_chat": _run_case(
            chat_url,
            _chat_payload(args.model, "Reply with exactly: pong"),
            _expect_text("pong"),
            5,
            args.timeout,
            args.api_key,
        ),
        "structured_simple": _run_case(
            chat_url,
            {
                **_chat_payload(args.model, "Return JSON with a status field.", max_tokens=64),
                "response_format": _response_format_schema(
                    "status_payload",
                    _object_schema({"status": {"type": "string"}}, ["status"]),
                ),
            },
            _expect_json_keys(["status"]),
            5,
            args.timeout,
            args.api_key,
        ),
        "structured_nested": _run_case(
            chat_url,
            {
                **_chat_payload(args.model, "Return JSON with a nested ticket object.", max_tokens=128),
                "response_format": _response_format_schema(
                    "ticket_payload",
                    _object_schema(
                        {
                            "ticket": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "status": {"type": "string"},
                                },
                                "required": ["id", "status"],
                                "additionalProperties": False,
                            }
                        },
                        ["ticket"],
                    ),
                ),
            },
            _expect_json_keys(["ticket"]),
            5,
            args.timeout,
            args.api_key,
        ),
        "auto_tool_noop": _run_case(
            chat_url,
            {
                **_chat_payload(args.model, "Use the noop tool once, then stop."),
                "tools": [tool_schema],
                "tool_choice": "auto",
            },
            _expect_tool_call("noop"),
            10,
            args.timeout,
            args.api_key,
        ),
        "auto_tool_arg": _run_case(
            chat_url,
            {
                **_chat_payload(args.model, "Use the noop tool exactly once with a short JSON object argument."),
                "tools": [tool_schema],
                "tool_choice": "auto",
            },
            _expect_tool_call("noop", "value"),
            10,
            args.timeout,
            args.api_key,
        ),
        "required_tool_arg": _run_case(
            chat_url,
            {
                **_chat_payload(args.model, "Use the noop tool exactly once with a short JSON object argument."),
                "tools": [tool_schema],
                "tool_choice": "required",
            },
            _expect_tool_call("noop", "value"),
            10,
            args.timeout,
            args.api_key,
        ),
        "named_tool_arg": _run_case(
            chat_url,
            {
                **_chat_payload(args.model, "Use the noop tool exactly once with a short JSON object argument."),
                "tools": [tool_schema],
                "tool_choice": {"type": "function", "function": {"name": "noop"}},
            },
            _expect_tool_call("noop", "value"),
            10,
            args.timeout,
            args.api_key,
        ),
        "large_schema_tool_stress": _run_case(
            chat_url,
            {
                **_chat_payload(
                    args.model,
                    "Call compose_summary once with a concise final status payload and no extra fields.",
                    max_tokens=384,
                ),
                "tools": [large_tool_schema],
                "tool_choice": "auto",
            },
            _expect_tool_call("compose_summary"),
            3,
            args.timeout,
            args.api_key,
        ),
        "responses_smoke": _run_case(
            responses_url,
            _response_payload(args.model, "Reply with exactly: responses-ok"),
            _expect_responses_text("responses-ok"),
            1,
            args.timeout,
            args.api_key,
        ),
    }
    results["concurrency_smoke"] = _run_concurrency(
        chat_url,
        _chat_payload(args.model, "Reply with exactly: concurrency-ok"),
        concurrency,
        requests,
        args.timeout,
        args.api_key,
    )
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
