from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from omlx_runtime_client import (  # noqa: E402
    OmlxRuntimeClient,
    OmlxRuntimeClientError,
    OmlxRuntimeContractError,
    OmlxRuntimeResponse,
    append_jsonl_record,
    build_failure_record,
    build_success_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 3 live validator for the oMLX runtime adapter."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=(
            "negative-contract",
            "liveness",
            "first-pass",
            "full-pass",
            "soak",
            "post-restart",
            "direct-control",
        ),
    )
    parser.add_argument("--base-url", required=True, help="Mini-local forwarded endpoint.")
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--fixture-specs",
        default=str(
            REPO_ROOT / "services" / "omlx-runtime" / "fixtures" / "phase3_fixture_specs.json"
        ),
    )
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--parity-repeats", type=int, default=2)
    parser.add_argument("--soak-minutes", type=float, default=45.0)
    return parser.parse_args()


def load_fixture_specs(path: str) -> tuple[dict[str, Any], str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    manifest_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload, manifest_hash


def ensure_dir(path: str) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def liveness_probe(base_url: str, bearer_token: str, timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/models",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
            "Connection": "close",
        },
        method="GET",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read()
    elapsed = time.monotonic() - started
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("liveness probe returned non-object JSON")
    return {
        "status_code": 200,
        "latency_seconds": elapsed,
        "response_bytes": len(raw),
        "payload": payload,
    }


def shape_signature(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: shape_signature(val) for key, val in sorted(value.items())}
    if isinstance(value, list):
        if not value:
            return []
        return [shape_signature(value[0])]
    return type(value).__name__


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def repeated_shared_prefix(block_template: str, repetitions: int) -> str:
    parts = []
    for index in range(repetitions):
        parts.append(block_template.format(index=index))
    return "".join(parts)


def build_payloads(specs: dict[str, Any], model: str, fixture_id: str) -> tuple[list[dict[str, Any]], str]:
    fixture = next(item for item in specs["fixtures"] if item["id"] == fixture_id)
    shared = repeated_shared_prefix(specs["shared_block"], fixture["shared_block_repetitions"])
    payloads: list[dict[str, Any]] = []
    for variant in range(fixture["concurrency"]):
        suffix = specs["suffix_template"].format(
            variant=variant,
            helper_index=(variant + fixture["shared_block_repetitions"]) % 13,
        ) * fixture["variant_suffix_repetitions"]
        payloads.append(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": specs["system_template"]},
                    {"role": "user", "content": shared + suffix},
                ],
                "temperature": 0,
                "top_p": 1,
                "max_tokens": fixture["max_tokens"],
                "stream": False,
            }
        )
    concurrency_class = f"c{fixture['concurrency']}"
    return payloads, concurrency_class


def raw_chat_completions(
    *,
    base_url: str,
    bearer_token: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> OmlxRuntimeResponse:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=encoded,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Connection": "close",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"direct upstream http {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"direct transport error: {exc}") from exc
    elapsed = time.monotonic() - started
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("direct path returned non-object JSON")
    return OmlxRuntimeResponse(
        status_code=200,
        body=parsed,
        elapsed_seconds=elapsed,
        request_bytes=len(encoded),
        response_bytes=len(raw),
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_summary(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl_record(path, payload)


def append_liveness_record(path: Path, stage: str, result: dict[str, Any]) -> None:
    append_jsonl_record(
        path,
        {
            "stage": stage,
            "status_code": result["status_code"],
            "latency_seconds": result["latency_seconds"],
            "response_bytes": result["response_bytes"],
            "model_ids": [
                entry.get("id")
                for entry in result["payload"].get("data", [])
                if isinstance(entry, dict)
            ],
        },
    )


def record_failure_body(path: Path, request_id: str, body: str) -> None:
    target = path / f"{request_id}.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def run_negative_contract(
    *, client: OmlxRuntimeClient, artifacts_dir: Path, manifest_hash: str, model: str
) -> None:
    cases = [
        ("stream_true", {"stream": True}),
        ("tools", {"tools": []}),
        ("tool_choice", {"tool_choice": "required"}),
        ("response_format", {"response_format": {"type": "json_schema"}}),
        (
            "content_array",
            {
                "messages": [
                    {"role": "system", "content": "valid"},
                    {"role": "user", "content": [{"type": "text", "text": "bad"}]},
                ]
            },
        ),
        ("responses_api", {"input": "hello", "messages": None}),
    ]
    valid_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a coding assistant."},
            {"role": "user", "content": "Summarize this fixture."},
        ],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 64,
        "stream": False,
    }
    results_path = artifacts_dir / "negative_contract.jsonl"
    for case_id, override in cases:
        payload = dict(valid_payload)
        payload.update(override)
        request_id = f"neg-{case_id}-{uuid4().hex[:8]}"
        try:
            client.chat_completions(payload)
        except OmlxRuntimeContractError as exc:
            append_jsonl_record(
                results_path,
                {
                    "request_id": request_id,
                    "fixture_id": case_id,
                    "manifest_hash": manifest_hash,
                    "target_model": model,
                    "status": "rejected_locally",
                    "failure_class": exc.failure_class,
                    "error_message": str(exc),
                },
            )
            continue
        raise RuntimeError(f"negative contract case {case_id} did not reject locally")


def request_runner(
    *,
    mode: str,
    base_url: str,
    bearer_token: str,
    payload: dict[str, Any],
    timeout_seconds: float,
    client: OmlxRuntimeClient,
) -> OmlxRuntimeResponse:
    if mode == "adapter":
        return client.chat_completions(payload)
    if mode == "direct":
        return raw_chat_completions(
            base_url=base_url,
            bearer_token=bearer_token,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
    raise ValueError(mode)


def run_block(
    *,
    mode: str,
    fixture_id: str,
    base_url: str,
    bearer_token: str,
    timeout_seconds: float,
    client: OmlxRuntimeClient,
    payloads: list[dict[str, Any]],
    manifest_hash: str,
    concurrency_class: str,
    artifacts_dir: Path,
) -> dict[str, Any]:
    requests_path = artifacts_dir / "requests.jsonl"
    errors_dir = artifacts_dir / "raw_errors"
    started = time.time()

    def one(index: int, payload: dict[str, Any]) -> tuple[str, float, Any]:
        request_id = f"{mode}-{fixture_id}-{index}-{uuid4().hex[:8]}"
        try:
            response = request_runner(
                mode=mode,
                base_url=base_url,
                bearer_token=bearer_token,
                payload=payload,
                timeout_seconds=timeout_seconds,
                client=client,
            )
            append_jsonl_record(
                requests_path,
                build_success_record(
                    request_id=request_id,
                    fixture_id=fixture_id,
                    manifest_hash=manifest_hash,
                    concurrency_class=concurrency_class,
                    target_model=payload["model"],
                    endpoint=base_url,
                    status_code=response.status_code,
                    latency_seconds=response.elapsed_seconds,
                    request_bytes=response.request_bytes,
                    response_bytes=response.response_bytes,
                ),
            )
            return request_id, response.elapsed_seconds, response
        except OmlxRuntimeClientError as exc:
            append_jsonl_record(
                requests_path,
                build_failure_record(
                    request_id=request_id,
                    fixture_id=fixture_id,
                    manifest_hash=manifest_hash,
                    concurrency_class=concurrency_class,
                    target_model=payload["model"],
                    endpoint=base_url,
                    failure_class=exc.failure_class,
                    error_message=str(exc),
                ),
            )
            if hasattr(exc, "body"):
                record_failure_body(errors_dir, request_id, getattr(exc, "body"))
            return request_id, math.inf, exc
        except Exception as exc:  # noqa: BLE001
            append_jsonl_record(
                requests_path,
                build_failure_record(
                    request_id=request_id,
                    fixture_id=fixture_id,
                    manifest_hash=manifest_hash,
                    concurrency_class=concurrency_class,
                    target_model=payload["model"],
                    endpoint=base_url,
                    failure_class="unexpected_error",
                    error_message=str(exc),
                ),
            )
            return request_id, math.inf, exc

    with ThreadPoolExecutor(max_workers=len(payloads)) as executor:
        results = list(executor.map(lambda pair: one(*pair), enumerate(payloads)))
    successes = [result for result in results if isinstance(result[2], OmlxRuntimeResponse)]
    latencies = [result[1] for result in successes]
    shapes = [shape_signature(result[2].body) for result in successes]
    summary = {
        "mode": mode,
        "fixture_id": fixture_id,
        "concurrency_class": concurrency_class,
        "started_at": started,
        "success_count": len(successes),
        "request_count": len(payloads),
        "p50_latency_seconds": percentile(latencies, 0.5) if latencies else None,
        "p95_latency_seconds": percentile(latencies, 0.95) if latencies else None,
        "max_latency_seconds": max(latencies) if latencies else None,
        "shape_signature": shapes[0] if shapes else None,
        "all_shapes_match": all(signature == shapes[0] for signature in shapes) if shapes else False,
    }
    append_summary(artifacts_dir / "summary.jsonl", summary)
    return summary


def compare_summaries(direct: dict[str, Any], adapter: dict[str, Any], *, fixture_id: str) -> None:
    if direct["success_count"] != direct["request_count"]:
        raise RuntimeError(f"direct {fixture_id} did not fully succeed")
    if adapter["success_count"] != adapter["request_count"]:
        raise RuntimeError(f"adapter {fixture_id} did not fully succeed")
    if direct["shape_signature"] != adapter["shape_signature"]:
        raise RuntimeError(f"shape mismatch for {fixture_id}")
    direct_p50 = direct["p50_latency_seconds"]
    adapter_p50 = adapter["p50_latency_seconds"]
    direct_p95 = direct["p95_latency_seconds"]
    adapter_p95 = adapter["p95_latency_seconds"]
    if direct_p50 is None or adapter_p50 is None:
        raise RuntimeError(f"missing p50 for {fixture_id}")
    if adapter_p50 > direct_p50 * 1.15:
        raise RuntimeError(f"adapter p50 overhead exceeded 15% for {fixture_id}")
    if fixture_id in {"S02", "S04"} and direct_p95 and adapter_p95 and adapter_p95 > direct_p95 * 1.20:
        raise RuntimeError(f"adapter p95 overhead exceeded 20% for {fixture_id}")


def run_parity_set(
    *,
    mode: str,
    fixture_ids: list[str],
    specs: dict[str, Any],
    manifest_hash: str,
    base_url: str,
    bearer_token: str,
    client: OmlxRuntimeClient,
    timeout_seconds: float,
    artifacts_dir: Path,
    model: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for fixture_id in fixture_ids:
        payloads, concurrency_class = build_payloads(specs, model, fixture_id)
        summary = run_block(
            mode=mode,
            fixture_id=fixture_id,
            base_url=base_url,
            bearer_token=bearer_token,
            timeout_seconds=timeout_seconds,
            client=client,
            payloads=payloads,
            manifest_hash=manifest_hash,
            concurrency_class=concurrency_class,
            artifacts_dir=artifacts_dir,
        )
        results.append(summary)
    return results


def run_parity_compare(
    *,
    fixture_ids: list[str],
    specs: dict[str, Any],
    manifest_hash: str,
    base_url: str,
    bearer_token: str,
    client: OmlxRuntimeClient,
    timeout_seconds: float,
    artifacts_dir: Path,
    model: str,
) -> None:
    direct_results = {
        summary["fixture_id"]: summary
        for summary in run_parity_set(
            mode="direct",
            fixture_ids=fixture_ids,
            specs=specs,
            manifest_hash=manifest_hash,
            base_url=base_url,
            bearer_token=bearer_token,
            client=client,
            timeout_seconds=timeout_seconds,
            artifacts_dir=artifacts_dir,
            model=model,
        )
    }
    adapter_results = {
        summary["fixture_id"]: summary
        for summary in run_parity_set(
            mode="adapter",
            fixture_ids=fixture_ids,
            specs=specs,
            manifest_hash=manifest_hash,
            base_url=base_url,
            bearer_token=bearer_token,
            client=client,
            timeout_seconds=timeout_seconds,
            artifacts_dir=artifacts_dir,
            model=model,
        )
    }
    for fixture_id in fixture_ids:
        compare_summaries(direct_results[fixture_id], adapter_results[fixture_id], fixture_id=fixture_id)


def run_soak(
    *,
    specs: dict[str, Any],
    manifest_hash: str,
    base_url: str,
    bearer_token: str,
    client: OmlxRuntimeClient,
    timeout_seconds: float,
    artifacts_dir: Path,
    soak_minutes: float,
    model: str,
) -> None:
    end_time = time.monotonic() + soak_minutes * 60.0
    sequence = ["S02", "S02", "S02", "S02", "S04"]
    iteration = 0
    while time.monotonic() < end_time:
        fixture_id = sequence[iteration % len(sequence)]
        payloads, concurrency_class = build_payloads(specs, model, fixture_id)
        run_block(
            mode="adapter",
            fixture_id=fixture_id,
            base_url=base_url,
            bearer_token=bearer_token,
            timeout_seconds=timeout_seconds,
            client=client,
            payloads=payloads,
            manifest_hash=manifest_hash,
            concurrency_class=concurrency_class,
            artifacts_dir=artifacts_dir,
        )
        iteration += 1


def main() -> int:
    global args
    args = parse_args()
    artifacts_dir = ensure_dir(args.artifacts_dir)
    specs, manifest_hash = load_fixture_specs(args.fixture_specs)
    client = OmlxRuntimeClient(
        base_url=args.base_url,
        bearer_token=args.bearer_token,
        timeout_seconds=args.timeout_seconds,
    )
    write_json(
        artifacts_dir / "run_manifest.json",
        {
            "mode": args.mode,
            "base_url": args.base_url,
            "model": args.model,
            "fixture_specs": args.fixture_specs,
            "manifest_hash": manifest_hash,
            "started_at_epoch": time.time(),
        },
    )
    if args.mode == "negative-contract":
        run_negative_contract(
            client=client,
            artifacts_dir=artifacts_dir,
            manifest_hash=manifest_hash,
            model=args.model,
        )
        return 0
    if args.mode == "liveness":
        result = liveness_probe(args.base_url, args.bearer_token, args.timeout_seconds)
        append_liveness_record(artifacts_dir / "liveness.jsonl", "liveness", result)
        return 0
    if args.mode == "first-pass":
        run_parity_compare(
            fixture_ids=["G01", "G02", "S02", "S04"],
            specs=specs,
            manifest_hash=manifest_hash,
            base_url=args.base_url,
            bearer_token=args.bearer_token,
            client=client,
            timeout_seconds=args.timeout_seconds,
            artifacts_dir=artifacts_dir,
            model=args.model,
        )
        return 0
    if args.mode == "full-pass":
        run_parity_compare(
            fixture_ids=["S01", "S03"],
            specs=specs,
            manifest_hash=manifest_hash,
            base_url=args.base_url,
            bearer_token=args.bearer_token,
            client=client,
            timeout_seconds=args.timeout_seconds,
            artifacts_dir=artifacts_dir,
            model=args.model,
        )
        return 0
    if args.mode == "soak":
        run_soak(
            specs=specs,
            manifest_hash=manifest_hash,
            base_url=args.base_url,
            bearer_token=args.bearer_token,
            client=client,
            timeout_seconds=args.timeout_seconds,
            artifacts_dir=artifacts_dir,
            soak_minutes=args.soak_minutes,
            model=args.model,
        )
        return 0
    if args.mode == "post-restart":
        run_parity_set(
            mode="adapter",
            fixture_ids=["G01", "S02", "S04"],
            specs=specs,
            manifest_hash=manifest_hash,
            base_url=args.base_url,
            bearer_token=args.bearer_token,
            client=client,
            timeout_seconds=args.timeout_seconds,
            artifacts_dir=artifacts_dir,
            model=args.model,
        )
        return 0
    if args.mode == "direct-control":
        run_parity_set(
            mode="direct",
            fixture_ids=["G01", "S02"],
            specs=specs,
            manifest_hash=manifest_hash,
            base_url=args.base_url,
            bearer_token=args.bearer_token,
            client=client,
            timeout_seconds=args.timeout_seconds,
            artifacts_dir=artifacts_dir,
            model=args.model,
        )
        return 0
    raise ValueError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
