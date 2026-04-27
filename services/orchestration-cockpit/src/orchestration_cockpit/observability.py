from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from omlx_runtime_client import append_jsonl_record

from orchestration_cockpit.state import CockpitState

DEFAULT_ARTIFACT_DIR = "/tmp/orchestration-cockpit-phase5"
DEFAULT_GRAPH_ID = "operator-cockpit"


def graph_id() -> str:
    return os.environ.get("ORCHESTRATION_COCKPIT_GRAPH_ID", DEFAULT_GRAPH_ID)


def artifact_dir() -> Path:
    return Path(os.environ.get("ORCHESTRATION_COCKPIT_ARTIFACT_DIR", DEFAULT_ARTIFACT_DIR))


def run_ledger_path() -> Path:
    return artifact_dir() / "run-ledger.jsonl"


def adapter_telemetry_path() -> Path:
    return artifact_dir() / "omlx-runtime-telemetry.jsonl"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_run_id() -> str:
    return f"run-{uuid4().hex[:12]}"


def new_adapter_request_id() -> str:
    return f"adapter-{uuid4().hex[:12]}"


def resolve_thread_id(
    state: CockpitState,
    config: Mapping[str, Any] | None,
) -> str:
    configurable = config.get("configurable", {}) if isinstance(config, Mapping) else {}
    thread_id = configurable.get("thread_id")
    if isinstance(thread_id, str) and thread_id.strip():
        return thread_id
    existing = state.get("thread_id")
    if isinstance(existing, str) and existing.strip():
        return existing
    return "local-thread"


def append_node_sequence(state: CockpitState, node_name: str) -> list[str]:
    return [*state.get("node_sequence", []), node_name]


def payload_manifest_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def append_run_ledger_record(record: Mapping[str, Any]) -> None:
    append_jsonl_record(run_ledger_path(), record)


def build_run_ledger_record(
    *,
    state: CockpitState,
    node_sequence: list[str],
    status: str,
    finished_at: str,
    latency_seconds: float | None,
) -> dict[str, Any]:
    return {
        "thread_id": state.get("thread_id", "local-thread"),
        "run_id": state.get("run_id", ""),
        "graph_id": graph_id(),
        "route_decision": state.get("route_decision", ""),
        "route_reason": state.get("route_reason", ""),
        "node_sequence": node_sequence,
        "fixture_id": state.get("fixture_id", ""),
        "adapter_request_id": state.get("adapter_request_id", ""),
        "status": status,
        "started_at": state.get("started_at", ""),
        "finished_at": finished_at,
        "latency_seconds": latency_seconds,
    }


def elapsed_seconds(started_at: str | None, finished_at: str) -> float | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((finished - started).total_seconds(), 6)
