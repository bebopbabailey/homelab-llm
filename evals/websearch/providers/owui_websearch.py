#!/usr/bin/env python3
"""Thin promptfoo provider for Open WebUI web search."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_API_BASE = "http://127.0.0.1:3000"
DEFAULT_TIMEOUT_MS = 120000


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _extract_domain(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host.lower()


def _collect_source_urls(payload: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for source_item in payload.get("sources") or []:
        source = source_item.get("source") or {}
        raw_urls = source.get("urls") or []
        for url in raw_urls:
            if isinstance(url, str):
                urls.append(url)
        for metadata in source_item.get("metadata") or []:
            source_url = metadata.get("source")
            if isinstance(source_url, str):
                urls.append(source_url)
    return _dedupe(urls)


def _iter_sse_json_lines(raw_bytes: bytes) -> Iterable[Dict[str, Any]]:
    for line in raw_bytes.decode("utf-8", errors="replace").splitlines():
        if not line.startswith("data: "):
            continue
        body = line[6:]
        if body.strip() == "[DONE]":
            break
        try:
            yield json.loads(body)
        except json.JSONDecodeError:
            continue


def _parse_stream_response(raw_bytes: bytes) -> Tuple[str, List[str], int]:
    answer_parts: List[str] = []
    source_urls: List[str] = []
    reasoning_chars = 0

    for payload in _iter_sse_json_lines(raw_bytes):
        source_urls.extend(_collect_source_urls(payload))
        for choice in payload.get("choices") or []:
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str):
                answer_parts.append(content)
            reasoning = delta.get("reasoning_content")
            if isinstance(reasoning, str):
                reasoning_chars += len(reasoning)
            message = choice.get("message") or {}
            message_content = message.get("content")
            if isinstance(message_content, str):
                answer_parts.append(message_content)

    answer_text = "".join(answer_parts).strip()
    return answer_text, _dedupe(source_urls), reasoning_chars


def _parse_json_response(raw_bytes: bytes) -> Tuple[str, List[str], int]:
    payload = json.loads(raw_bytes.decode("utf-8", errors="replace") or "{}")
    source_urls = _collect_source_urls(payload)
    answer_parts: List[str] = []
    for choice in payload.get("choices") or []:
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            answer_parts.append(content)
    return "\n".join(answer_parts).strip(), source_urls, 0


def call_api(prompt: str, options: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    config = (options or {}).get("config") or {}
    metadata = ((context or {}).get("test") or {}).get("metadata") or {}
    api_key = os.getenv("OWUI_API_KEY")
    if not api_key:
        return {"error": "OWUI_API_KEY is required"}

    api_base = str(config.get("apiBase") or os.getenv("OWUI_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    model = config.get("model")
    if not model:
        return {"error": "provider config.model is required"}

    stream = bool(config.get("stream", True))
    timeout_ms = int(config.get("timeoutMs") or DEFAULT_TIMEOUT_MS)
    timeout_s = max(timeout_ms / 1000.0, 1.0)

    body = {
        "model": model,
        "stream": stream,
        "messages": [{"role": "user", "content": prompt}],
        "features": {"web_search": True},
    }

    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{api_base}/api/chat/completions",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {"error": f"HTTP {exc.code}: {detail or exc.reason}"}
    except Exception as exc:  # pragma: no cover - transport errors
        return {"error": f"request_failed: {exc}"}

    latency_ms = round((time.perf_counter() - started) * 1000.0, 2)

    try:
        if stream:
            answer_text, source_urls, reasoning_chars = _parse_stream_response(raw)
            response_mode = "sse"
        else:
            answer_text, source_urls, reasoning_chars = _parse_json_response(raw)
            response_mode = "json"
    except Exception as exc:
        return {"error": f"parse_failed: {exc}"}

    source_domains = _dedupe(_extract_domain(url) for url in source_urls if url)

    return {
        "output": answer_text,
        "latencyMs": latency_ms,
        "metadata": {
            "target": "owui",
            "model": model,
            "query_id": metadata.get("id") or metadata.get("query_id"),
            "category": metadata.get("category"),
            "freshness_level": metadata.get("freshness_level"),
            "expected_source_type": metadata.get("expected_source_type"),
            "source_urls": source_urls,
            "source_domains": source_domains,
            "source_count": len(source_urls),
            "stream_mode": stream,
            "response_mode": response_mode,
            "reasoning_chars": reasoning_chars,
            "request_path": "/api/chat/completions",
        },
    }
