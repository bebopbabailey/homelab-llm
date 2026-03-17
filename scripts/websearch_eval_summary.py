#!/usr/bin/env python3
"""Summarize saved promptfoo web-search eval results as markdown."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse


DEFAULT_BLOCKED_DOMAINS = Path("evals/websearch/blocked_domains.txt")
JUNK_DOMAIN_PATTERNS = (
    "quora.com",
    "zhihu.com",
    "pinterest.",
    "stackexchange.com",
)
SMOKE_LATENCY_THRESHOLD_MS = 120000.0


def _load_results(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text())
    results = payload.get("results") or {}
    if isinstance(results, dict):
        nested_results = results.get("results") or []
        if isinstance(nested_results, list):
            return nested_results
        return []
    if isinstance(results, list):
        return results
    return []


def _load_blocked_domains(path: Path) -> List[str]:
    domains: List[str] = []
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip().lower().rstrip(".")
        if not line or line.startswith("#"):
            continue
        domains.append(line)
    return domains


def _extract_domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def _normalize_domains(response_meta: Dict[str, Any]) -> List[str]:
    domains = response_meta.get("source_domains") or []
    seen = set()
    normalized: List[str] = []
    for item in domains:
        if not isinstance(item, str):
            continue
        domain = item.strip().lower().rstrip(".")
        if not domain or domain in seen:
            continue
        seen.add(domain)
        normalized.append(domain)
    if normalized:
        return normalized
    for item in response_meta.get("source_urls") or []:
        if not isinstance(item, str):
            continue
        domain = _extract_domain(item)
        if not domain or domain in seen:
            continue
        seen.add(domain)
        normalized.append(domain)
    return normalized


def _blocked_matches(domains: Iterable[str], blocked_domains: List[str]) -> List[str]:
    matches: List[str] = []
    seen = set()
    for domain in domains:
        for blocked in blocked_domains:
            if domain == blocked or domain.endswith(f".{blocked}"):
                if domain not in seen:
                    seen.add(domain)
                    matches.append(domain)
                break
    return matches


def _p95(values: List[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _matches(filters: argparse.Namespace, result: Dict[str, Any]) -> bool:
    provider = ((result.get("provider") or {}).get("label") or (result.get("provider") or {}).get("id") or "")
    metadata = (result.get("testCase") or {}).get("metadata") or {}
    if filters.provider_regex and not re.search(filters.provider_regex, provider):
        return False
    if filters.category and metadata.get("category") != filters.category:
        return False
    if filters.freshness_level and metadata.get("freshness_level") != filters.freshness_level:
        return False
    return True


def _format_delta(left: float | int | None, right: float | int | None) -> str:
    if left is None or right is None:
        return "n/a"
    delta = right - left
    if isinstance(delta, float):
        return f"{delta:+.2f}"
    return f"{delta:+d}"


def _get_latency(result: Dict[str, Any]) -> float | None:
    response = result.get("response") or {}
    latency = response.get("latencyMs")
    if latency is None:
        latency = result.get("latencyMs")
    return float(latency) if latency is not None else None


def _provider_stats(group: List[Dict[str, Any]], blocked_domains: List[str]) -> Dict[str, Any]:
    latencies: List[float] = []
    errors = 0
    assertion_failures = 0
    empty_outputs = 0
    zero_source_cases = 0
    blocked_hits = 0
    smoke_latency_cases = 0
    top_domains: Counter[str] = Counter()
    junk_domains: Counter[str] = Counter()
    blocked_case_lines: List[str] = []
    zero_source_lines: List[str] = []
    empty_lines: List[str] = []

    for result in group:
        metadata = (result.get("testCase") or {}).get("metadata") or {}
        query_id = metadata.get("id") or (result.get("testCase") or {}).get("description") or "unknown"
        response = result.get("response") or {}
        response_meta = response.get("metadata") or {}
        output = (response.get("output") or "").strip()
        domains = _normalize_domains(response_meta)
        source_count = int(response_meta.get("source_count") or 0)
        latency = _get_latency(result)
        if latency is not None:
            latencies.append(latency)
        if response.get("error") or (result.get("error") and not result.get("gradingResult")):
            errors += 1
        if not ((result.get("gradingResult") or {}).get("pass", True)):
            assertion_failures += 1
        if not output:
            empty_outputs += 1
            empty_lines.append(f"{query_id}")
        if source_count <= 0:
            zero_source_cases += 1
            zero_source_lines.append(f"{query_id}")
        matches = _blocked_matches(domains, blocked_domains)
        if matches:
            blocked_hits += 1
            blocked_case_lines.append(f"{query_id}: {', '.join(matches)}")
        if metadata.get("smoke") and latency is not None and latency >= SMOKE_LATENCY_THRESHOLD_MS:
            smoke_latency_cases += 1
        for domain in domains:
            top_domains[domain] += 1
            if any(pattern in domain for pattern in JUNK_DOMAIN_PATTERNS):
                junk_domains[domain] += 1

    return {
        "count": len(group),
        "errors": errors,
        "assertion_failures": assertion_failures,
        "empty_outputs": empty_outputs,
        "zero_source_cases": zero_source_cases,
        "blocked_hits": blocked_hits,
        "smoke_latency_cases": smoke_latency_cases,
        "median_latency": median(latencies) if latencies else None,
        "p95_latency": _p95(latencies),
        "top_domains": top_domains,
        "junk_domains": junk_domains,
        "blocked_case_lines": blocked_case_lines,
        "zero_source_lines": zero_source_lines,
        "empty_lines": empty_lines,
    }


def _render_summary(inputs: List[Path], results: List[Dict[str, Any]], blocked_domains_path: Path) -> str:
    blocked_domains = _load_blocked_domains(blocked_domains_path)
    provider_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    category_counts: Counter[str] = Counter()
    category_by_provider: Dict[str, Counter[str]] = defaultdict(Counter)

    for result in results:
        provider = ((result.get("provider") or {}).get("label") or (result.get("provider") or {}).get("id") or "unknown")
        provider_groups[provider].append(result)
        metadata = (result.get("testCase") or {}).get("metadata") or {}
        category = str(metadata.get("category") or "unknown")
        category_counts[category] += 1
        category_by_provider[provider][category] += 1

    provider_stats = {
        provider: _provider_stats(group, blocked_domains)
        for provider, group in provider_groups.items()
    }

    lines: List[str] = []
    lines.append("# Websearch Eval Summary")
    lines.append("")
    lines.append("## Inputs")
    for path in inputs:
        lines.append(f"- `{path}`")
    lines.append(f"- blocked domains: `{blocked_domains_path}`")
    lines.append("")
    lines.append("## Totals")
    lines.append(f"- Results: {len(results)}")
    lines.append(f"- Providers: {', '.join(sorted(provider_groups)) or 'none'}")
    lines.append("")
    lines.append("## Categories")
    for category, count in sorted(category_counts.items()):
        lines.append(f"- `{category}`: {count}")
    lines.append("")
    lines.append("## Category Breakdown By Provider")
    providers = sorted(provider_groups)
    if providers:
        lines.append("| category | " + " | ".join(providers) + " |")
        lines.append("| --- | " + " | ".join(["---:"] * len(providers)) + " |")
        for category in sorted(category_counts):
            values = [str(category_by_provider[provider].get(category, 0)) for provider in providers]
            lines.append("| " + " | ".join([category] + values) + " |")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Provider Breakdown")
    for provider in providers:
        stats = provider_stats[provider]
        lines.append(f"### {provider}")
        lines.append(f"- Cases: {stats['count']}")
        lines.append(f"- Errors: {stats['errors']}")
        lines.append(f"- Assertion failures: {stats['assertion_failures']}")
        lines.append(f"- Empty outputs: {stats['empty_outputs']}")
        lines.append(f"- Zero-source cases: {stats['zero_source_cases']}")
        lines.append(f"- Blocked-domain hits: {stats['blocked_hits']}")
        lines.append(f"- Smoke latency diagnostics (>= {SMOKE_LATENCY_THRESHOLD_MS:.0f} ms): {stats['smoke_latency_cases']}")
        if stats["median_latency"] is not None:
            lines.append(f"- Median latency ms: {stats['median_latency']:.2f}")
        if stats["p95_latency"] is not None:
            lines.append(f"- P95 latency ms: {stats['p95_latency']:.2f}")
        top_domains = stats["top_domains"].most_common(10)
        if top_domains:
            lines.append("- Top domains:")
            for domain, count in top_domains:
                lines.append(f"  - `{domain}`: {count}")
        junk = stats["junk_domains"].most_common(10)
        if junk:
            lines.append("- Likely junk domains:")
            for domain, count in junk:
                lines.append(f"  - `{domain}`: {count}")
        lines.append("")

    fast_label = "owui-fast"
    deep_label = "owui-research"
    if fast_label in provider_stats and deep_label in provider_stats:
        fast_stats = provider_stats[fast_label]
        deep_stats = provider_stats[deep_label]
        lines.append("## Fast vs Deep Comparison")
        lines.append("")
        lines.append("| metric | owui-fast | owui-research | delta (research-fast) |")
        lines.append("| --- | ---: | ---: | ---: |")
        rows = [
            ("cases", fast_stats["count"], deep_stats["count"]),
            ("errors", fast_stats["errors"], deep_stats["errors"]),
            ("assertion failures", fast_stats["assertion_failures"], deep_stats["assertion_failures"]),
            ("empty outputs", fast_stats["empty_outputs"], deep_stats["empty_outputs"]),
            ("zero-source cases", fast_stats["zero_source_cases"], deep_stats["zero_source_cases"]),
            ("blocked-domain hits", fast_stats["blocked_hits"], deep_stats["blocked_hits"]),
            (f"smoke latency diagnostics >= {SMOKE_LATENCY_THRESHOLD_MS:.0f} ms", fast_stats["smoke_latency_cases"], deep_stats["smoke_latency_cases"]),
            ("median latency ms", fast_stats["median_latency"], deep_stats["median_latency"]),
            ("p95 latency ms", fast_stats["p95_latency"], deep_stats["p95_latency"]),
        ]
        for label, fast_value, deep_value in rows:
            if isinstance(fast_value, float) or isinstance(deep_value, float):
                fast_str = f"{fast_value:.2f}" if fast_value is not None else "n/a"
                deep_str = f"{deep_value:.2f}" if deep_value is not None else "n/a"
            else:
                fast_str = str(fast_value)
                deep_str = str(deep_value)
            lines.append(f"| {label} | {fast_str} | {deep_str} | {_format_delta(fast_value, deep_value)} |")
        lines.append("")

    blocked_lines: List[str] = []
    zero_source_lines: List[str] = []
    empty_lines: List[str] = []
    smoke_latency_lines: List[str] = []
    for provider in providers:
        stats = provider_stats[provider]
        blocked_lines.extend(f"{provider}: {item}" for item in stats["blocked_case_lines"])
        zero_source_lines.extend(f"{provider}: {item}" for item in stats["zero_source_lines"])
        empty_lines.extend(f"{provider}: {item}" for item in stats["empty_lines"])
        if stats["smoke_latency_cases"]:
            for result in provider_groups[provider]:
                metadata = (result.get("testCase") or {}).get("metadata") or {}
                if not metadata.get("smoke"):
                    continue
                latency = _get_latency(result)
                if latency is None or latency < SMOKE_LATENCY_THRESHOLD_MS:
                    continue
                query_id = metadata.get("id") or (result.get("testCase") or {}).get("description") or "unknown"
                smoke_latency_lines.append(f"{provider}: {query_id} ({latency:.2f} ms)")

    if blocked_lines:
        lines.append("## Blocked-Domain Hits")
        for item in blocked_lines[:50]:
            lines.append(f"- `{item}`")
        lines.append("")
    if zero_source_lines:
        lines.append("## Zero-Source Cases")
        for item in zero_source_lines[:50]:
            lines.append(f"- `{item}`")
        lines.append("")
    if empty_lines:
        lines.append("## Empty Outputs")
        for item in empty_lines[:50]:
            lines.append(f"- `{item}`")
        lines.append("")
    if smoke_latency_lines:
        lines.append("## Smoke Latency Diagnostics")
        lines.append(f"- Diagnostic only; not a product-quality gate. Threshold: `{SMOKE_LATENCY_THRESHOLD_MS:.0f} ms`")
        for item in smoke_latency_lines[:50]:
            lines.append(f"- `{item}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize promptfoo web-search eval results.")
    parser.add_argument("--input", action="append", required=True, help="Promptfoo JSON output file")
    parser.add_argument("--output", help="Write markdown summary to this path")
    parser.add_argument("--provider-regex", help="Regex filter on provider label/id")
    parser.add_argument("--category", help="Only include this category")
    parser.add_argument("--freshness-level", help="Only include this freshness level")
    parser.add_argument("--blocked-domains", default=str(DEFAULT_BLOCKED_DOMAINS), help="Blocked domain policy file")
    args = parser.parse_args()

    input_paths = [Path(item) for item in args.input]
    blocked_domains_path = Path(args.blocked_domains)
    results: List[Dict[str, Any]] = []
    for path in input_paths:
        for result in _load_results(path):
            if _matches(args, result):
                results.append(result)

    summary = _render_summary(input_paths, results, blocked_domains_path)
    if args.output:
        Path(args.output).write_text(summary)
    else:
        print(summary, end="")


if __name__ == "__main__":
    main()
