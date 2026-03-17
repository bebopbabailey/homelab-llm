#!/usr/bin/env python3
"""Deterministic promptfoo assertions for web-search evals."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Set
from urllib.parse import urlparse

BLOCKED_DOMAINS_PATH = Path(__file__).with_name("blocked_domains.txt")


def _grading_result(passed: bool, reason: str) -> Dict[str, Any]:
    return {
        "pass": passed,
        "score": 1 if passed else 0,
        "reason": reason,
    }


def _normalize_domain(value: str) -> str:
    return value.strip().lower().rstrip(".")


def load_blocked_domains(path: str | None = None) -> Set[str]:
    blocked_path = Path(path) if path else BLOCKED_DOMAINS_PATH
    domains: Set[str] = set()
    for raw_line in blocked_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        domains.add(_normalize_domain(line))
    return domains


def _extract_domain_from_url(url: str) -> str:
    try:
        return _normalize_domain(urlparse(url).hostname or "")
    except ValueError:
        return ""


def _dedupe(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    output: List[str] = []
    for item in items:
        normalized = _normalize_domain(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def normalize_source_domains(context: Dict[str, Any]) -> List[str]:
    provider_response = (context or {}).get("providerResponse") or {}
    metadata = provider_response.get("metadata") or {}
    source_domains = metadata.get("source_domains") or []
    if isinstance(source_domains, list) and source_domains:
        return _dedupe(str(item) for item in source_domains if isinstance(item, str))
    source_urls = metadata.get("source_urls") or []
    return _dedupe(_extract_domain_from_url(item) for item in source_urls if isinstance(item, str))


def _blocked_matches(domains: Iterable[str], blocked_domains: Set[str]) -> List[str]:
    matches: List[str] = []
    for domain in domains:
        normalized = _normalize_domain(domain)
        for blocked in blocked_domains:
            if normalized == blocked or normalized.endswith(f".{blocked}"):
                matches.append(normalized)
                break
    return _dedupe(matches)


def assert_non_empty_output(output: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(output, str) and output.strip():
        return _grading_result(True, "non-empty output")
    query_id = ((context or {}).get("test") or {}).get("metadata", {}).get("id") or "unknown"
    return _grading_result(False, f"empty output for {query_id}")


def assert_no_blocked_domains(output: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    domains = normalize_source_domains(context)
    blocked_domains = load_blocked_domains()
    matches = _blocked_matches(domains, blocked_domains)
    if matches:
        return _grading_result(False, f"blocked source domains detected: {', '.join(matches)}")
    return _grading_result(True, "no blocked domains detected")


def assert_expected_sources(output: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    test_metadata = ((context or {}).get("test") or {}).get("metadata") or {}
    if not test_metadata.get("expects_sources"):
        return _grading_result(True, "not_applicable")
    provider_response = (context or {}).get("providerResponse") or {}
    response_metadata = provider_response.get("metadata") or {}
    source_count = response_metadata.get("source_count") or 0
    if source_count >= 1:
        return _grading_result(True, f"source_count={source_count}")
    query_id = test_metadata.get("id") or "unknown"
    return _grading_result(False, f"expected at least one source for {query_id}; source_count={source_count}")
