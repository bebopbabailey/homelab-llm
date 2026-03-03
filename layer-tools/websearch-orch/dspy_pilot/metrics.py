"""Citation-fidelity scoring metrics for DSPy pilot runs."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any
from urllib.parse import urlparse

from .models import CitationCase, ModelPrediction

PLACEHOLDER_HOSTS = {"example.com", "example.org", "example.net"}


def normalize_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    return f"{scheme}://{host}{path}"


def is_placeholder_url(url: str) -> bool:
    normalized = normalize_url(url)
    if not normalized:
        return True
    parsed = urlparse(normalized)
    host = parsed.netloc
    if host in PLACEHOLDER_HOSTS:
        return True
    if "placeholder" in host:
        return True
    if "/example" in parsed.path.lower():
        return True
    return False


def score_case(case: CitationCase, prediction: ModelPrediction) -> dict[str, Any]:
    allowed_ids = {source.source_id for source in case.retrieved_sources}
    allowed_url_to_id = {
        normalize_url(source.url): source.source_id
        for source in case.retrieved_sources
        if normalize_url(source.url)
    }

    citations = prediction.citations
    citation_total = len(citations)
    valid_hits = 0
    placeholder_hits = 0
    claim_span_hits = 0
    matched_source_ids: set[int] = set()
    invalid_citations: list[dict[str, Any]] = []

    for citation in citations:
        normalized_url = normalize_url(citation.url)
        source_id = citation.source_id
        if citation.url and is_placeholder_url(citation.url):
            placeholder_hits += 1

        if source_id not in allowed_ids and normalized_url in allowed_url_to_id:
            source_id = allowed_url_to_id[normalized_url]
        if source_id in allowed_ids:
            valid_hits += 1
            matched_source_ids.add(source_id)
        else:
            invalid_citations.append({"source_id": citation.source_id, "url": citation.url})

        if len(citation.claim_span.strip()) >= 12:
            claim_span_hits += 1

    citation_validity = (valid_hits / citation_total) if citation_total else 0.0
    must_include = set(case.expected.must_include_source_ids)
    if must_include:
        citation_specificity = len(matched_source_ids.intersection(must_include)) / len(must_include)
    else:
        specificity_denom = min(3, max(1, len(allowed_ids)))
        citation_specificity = min(1.0, len(matched_source_ids) / specificity_denom)

    groundedness_proxy = (claim_span_hits / citation_total) if citation_total else 0.0
    placeholder_rate = (placeholder_hits / citation_total) if citation_total else 0.0
    min_citations_met = citation_total >= max(1, case.expected.min_citations)
    placeholder_hard_fail = case.expected.forbid_placeholder_urls and placeholder_hits > 0

    weighted_score = (
        (0.45 * citation_validity)
        + (0.30 * citation_specificity)
        + (0.20 * groundedness_proxy)
        + (0.05 * (1.0 - placeholder_rate))
    )
    if not min_citations_met:
        weighted_score *= 0.6
    if placeholder_hard_fail:
        weighted_score = 0.0
    weighted_score = max(0.0, min(1.0, weighted_score))

    status = "pass" if weighted_score >= 0.75 and min_citations_met and not placeholder_hard_fail else "fail"
    return {
        "case_id": case.case_id,
        "status": status,
        "score": round(weighted_score, 4),
        "metrics": {
            "citation_validity": round(citation_validity, 4),
            "citation_specificity": round(citation_specificity, 4),
            "groundedness_proxy": round(groundedness_proxy, 4),
            "placeholder_rate": round(placeholder_rate, 4),
            "min_citations_met": min_citations_met,
        },
        "counts": {
            "citations_total": citation_total,
            "valid_hits": valid_hits,
            "placeholder_hits": placeholder_hits,
            "claim_span_hits": claim_span_hits,
            "matched_source_ids": sorted(matched_source_ids),
        },
        "invalid_citations": invalid_citations,
    }


def aggregate_scores(case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    if not case_scores:
        return {
            "cases_total": 0,
            "cases_passed": 0,
            "pass_rate": 0.0,
            "mean_score": 0.0,
            "status_counts": {},
        }

    status_counts = Counter(item.get("status", "unknown") for item in case_scores)
    score_values = [float(item.get("score", 0.0)) for item in case_scores]
    return {
        "cases_total": len(case_scores),
        "cases_passed": int(status_counts.get("pass", 0)),
        "pass_rate": round(float(status_counts.get("pass", 0)) / len(case_scores), 4),
        "mean_score": round(mean(score_values), 4),
        "status_counts": dict(status_counts),
    }

