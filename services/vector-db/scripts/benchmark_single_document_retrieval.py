#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from typing import Any


def _post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}


def _run_mode(base_url: str, payload: dict[str, Any], runs: int) -> dict[str, Any]:
    latencies: list[float] = []
    last_hits: list[dict[str, Any]] = []
    for _ in range(runs):
        started = time.perf_counter()
        response = _post(f"{base_url.rstrip('/')}/v1/memory/search", payload)
        latencies.append((time.perf_counter() - started) * 1000.0)
        hits = response.get("hits")
        last_hits = list(hits) if isinstance(hits, list) else []
    return {
        "p50_latency_ms": round(statistics.median(latencies), 3),
        "p95_latency_ms": round(statistics.quantiles(latencies, n=100, method="inclusive")[94], 3) if len(latencies) > 1 else round(latencies[0], 3),
        "top_chunk_ids": [str(hit.get("chunk_id", "")) for hit in last_hits[:5]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark exact vs approximate single-document retrieval")
    parser.add_argument("--api-base", default="http://127.0.0.1:55440")
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    common = {
        "query": args.query,
        "profile": "balanced",
        "document_id": args.document_id,
        "top_k": 10,
        "lexical_k": 48,
        "vector_k": 48,
        "num_candidates": 192,
        "final_k": 10,
    }
    exact = _run_mode(args.api_base, {**common, "vector_search_mode": "exact"}, args.runs)
    approximate = _run_mode(args.api_base, {**common, "vector_search_mode": "approximate"}, args.runs)
    overlap = sorted(set(exact["top_chunk_ids"]) & set(approximate["top_chunk_ids"]))
    print(json.dumps({"exact": exact, "approximate": approximate, "top5_overlap": overlap}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
