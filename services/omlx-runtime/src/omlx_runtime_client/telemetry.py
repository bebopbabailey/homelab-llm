from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def build_success_record(
    *,
    request_id: str,
    fixture_id: str,
    manifest_hash: str,
    concurrency_class: str,
    target_model: str,
    endpoint: str,
    status_code: int,
    latency_seconds: float,
    request_bytes: int,
    response_bytes: int,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "fixture_id": fixture_id,
        "manifest_hash": manifest_hash,
        "concurrency_class": concurrency_class,
        "target_model": target_model,
        "endpoint": endpoint,
        "status_code": status_code,
        "latency_seconds": latency_seconds,
        "request_bytes": request_bytes,
        "response_bytes": response_bytes,
        "failure_class": None,
    }


def build_failure_record(
    *,
    request_id: str,
    fixture_id: str,
    manifest_hash: str,
    concurrency_class: str,
    target_model: str,
    endpoint: str,
    failure_class: str,
    error_message: str,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "fixture_id": fixture_id,
        "manifest_hash": manifest_hash,
        "concurrency_class": concurrency_class,
        "target_model": target_model,
        "endpoint": endpoint,
        "status_code": None,
        "latency_seconds": None,
        "request_bytes": None,
        "response_bytes": None,
        "failure_class": failure_class,
        "error_message": error_message,
    }


def append_jsonl_record(path: str | Path, record: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), sort_keys=True))
        handle.write("\n")
