#!/usr/bin/env python3
"""Phase A baseline helper for Open WebUI web-search validation.

Usage:
  1) Print end-user query pack with a run id:
     python3 scripts/openwebui_phase_a_baseline.py print-pack --run-id PHASEA-001
  2) Run those prompts manually in Open WebUI.
  3) Score logs from CLI:
     python3 scripts/openwebui_phase_a_baseline.py score --since "30 minutes ago" --run-id PHASEA-001
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class QueryCase:
    case_id: str
    prompt: str


QUERY_PACK: list[QueryCase] = [
    QueryCase("Q01", "Find three beginner wok-cooking techniques with reputable sources."),
    QueryCase("Q02", "Compare cast iron vs carbon steel woks for home use."),
    QueryCase("Q03", "What are current best practices for sourdough starter care?"),
    QueryCase("Q04", "Summarize two recent developments in residential solar batteries."),
    QueryCase("Q05", "Best practices for home lab backup strategy with 3-2-1 model."),
    QueryCase("Q06", "How to secure Tailscale service exposure in a homelab."),
    QueryCase("Q07", "What are signs a DNS resolver is misconfigured in a LAN?"),
    QueryCase("Q08", "Beginner guide to induction wok burners and heat output."),
    QueryCase("Q09", "How to evaluate source reliability for technical tutorials."),
    QueryCase("Q10", "What changed recently in SearXNG engine reliability guidance?"),
]


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout


def print_pack(run_id: str) -> int:
    print(f"# Open WebUI Phase A Query Pack")
    print(f"# run_id={run_id}")
    print("# Send each prompt as a separate message in Open WebUI with web search enabled.\n")
    for q in QUERY_PACK:
        print(f"[{run_id}:{q.case_id}] {q.prompt}")
    return 0


def _journal(service: str, since: str) -> str:
    return _run(["journalctl", "-u", service, "--since", since, "--no-pager"])


def _iter_run_cases(run_id: str) -> Iterable[str]:
    for q in QUERY_PACK:
        yield f"{run_id}:{q.case_id}"


def _sum_int_matches(pattern: str, text: str) -> int:
    values = re.findall(pattern, text, flags=re.IGNORECASE)
    total = 0
    for value in values:
        try:
            total += int(value)
        except ValueError:
            continue
    return total


def score(run_id: str, since: str) -> int:
    owui = _journal("open-webui.service", since)
    searx = _journal("searxng.service", since)
    orch = _journal("websearch-orch.service", since)

    # Per-run markers in Open WebUI logs.
    run_hits: dict[str, int] = {}
    source_hits: dict[str, int] = {}
    for marker in _iter_run_cases(run_id):
        run_hits[marker] = len(re.findall(re.escape(marker), owui))
        source_hits[marker] = len(
            re.findall(rf"<source id=.*{re.escape(marker)}", owui, flags=re.IGNORECASE)
        )

    retrieval_errors = len(
        re.findall(
            r"SearxEngineTooManyRequestsException|Too many request|HTTP error 429",
            searx,
            flags=re.IGNORECASE,
        )
    )
    extraction_markers = len(re.findall(r"<source id=", owui))
    searx_json_markers = len(re.findall(r"OWUI_SEARXNG_RAW_JSON", owui))

    citation_total = len(re.findall(r"citation_map_status=", orch, flags=re.IGNORECASE))
    citation_ready = len(re.findall(r"citation_map_status=ready", orch, flags=re.IGNORECASE))
    grounding_total = len(re.findall(r"grounding_status=", orch, flags=re.IGNORECASE))
    grounding_warn = len(re.findall(r"grounding_status=warn", orch, flags=re.IGNORECASE))
    budget_drop_events = len(re.findall(r"budget_drops=[1-9]\d*", orch, flags=re.IGNORECASE))
    dedupe_drop_events = len(re.findall(r"dedupe_drops=[1-9]\d*", orch, flags=re.IGNORECASE))
    domain_cap_drop_events = len(re.findall(r"domain_cap_drops=[1-9]\d*", orch, flags=re.IGNORECASE))
    placeholder_drop_events = len(re.findall(r"placeholder_drops': [1-9]\d*", orch, flags=re.IGNORECASE))
    unsupported_claim_count_total = _sum_int_matches(r"unsupported_claim_count=(\d+)", orch)

    citation_ready_rate = round(citation_ready / citation_total, 4) if citation_total else None
    grounding_warn_rate = round(grounding_warn / grounding_total, 4) if grounding_total else None

    prompted = sum(1 for _, c in run_hits.items() if c > 0)
    with_sources = sum(1 for _, c in source_hits.items() if c > 0)

    report = {
        "run_id": run_id,
        "since": since,
        "cases_total": len(QUERY_PACK),
        "cases_seen_in_openwebui_logs": prompted,
        "cases_with_source_blocks": with_sources,
        "openwebui_source_block_count": extraction_markers,
        "openwebui_raw_searx_markers": searx_json_markers,
        "searx_rate_limit_or_429_errors": retrieval_errors,
        "phase2_quality": {
            "citation_map_total": citation_total,
            "citation_map_ready": citation_ready,
            "citation_map_ready_rate": citation_ready_rate,
            "grounding_gate_total": grounding_total,
            "grounding_gate_warn": grounding_warn,
            "grounding_warn_rate": grounding_warn_rate,
            "placeholder_drop_events": placeholder_drop_events,
            "unsupported_claim_count_total": unsupported_claim_count_total,
            "budget_drop_events": budget_drop_events,
            "dedupe_drop_events": dedupe_drop_events,
            "domain_cap_drop_events": domain_cap_drop_events,
        },
        "per_case_markers": run_hits,
        "per_case_sources": source_hits,
        "pass_fail": {
            "retrieval_stability": retrieval_errors == 0,
            "all_cases_seen": prompted == len(QUERY_PACK),
            "all_cases_have_sources": with_sources == len(QUERY_PACK),
        },
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Open WebUI Phase A baseline helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("print-pack", help="Print query pack for manual Open WebUI run")
    p_pack.add_argument("--run-id", required=True, help="Unique run id, e.g. PHASEA-20260218-1")

    p_score = sub.add_parser("score", help="Score logs for a previously-run query pack")
    p_score.add_argument("--run-id", required=True)
    p_score.add_argument("--since", default="30 minutes ago")

    args = parser.parse_args()
    if args.cmd == "print-pack":
        return print_pack(args.run_id)
    if args.cmd == "score":
        return score(args.run_id, args.since)
    return 1


if __name__ == "__main__":
    sys.exit(main())
