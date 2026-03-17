#!/usr/bin/env python3
"""Generate a reviewer-friendly packet from saved web-search eval artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

SCORE_HEADERS = [
    "profile_id",
    "lane",
    "run_id",
    "query_id",
    "usefulness_score",
    "citation_quality_score",
    "freshness_score",
    "junk_domain_score",
    "comments",
]


def _load_results(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text())
    results = payload.get("results") or {}
    if isinstance(results, dict):
        nested = results.get("results") or []
        return nested if isinstance(nested, list) else []
    if isinstance(results, list):
        return results
    return []


def _safe_slug(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in text).strip("-")


def _extract_domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def _normalize_domains(meta: Dict[str, Any]) -> List[str]:
    seen = set()
    domains: List[str] = []
    for item in meta.get("source_domains") or []:
        if not isinstance(item, str):
            continue
        domain = item.strip().lower().rstrip(".")
        if domain and domain not in seen:
            seen.add(domain)
            domains.append(domain)
    if domains:
        return domains
    for item in meta.get("source_urls") or []:
        if not isinstance(item, str):
            continue
        domain = _extract_domain(item)
        if domain and domain not in seen:
            seen.add(domain)
            domains.append(domain)
    return domains


def _lane(provider: Dict[str, Any]) -> str:
    return (provider or {}).get("label") or (provider or {}).get("id") or "unknown"


def _slice_name(path: Path) -> str:
    stem = path.stem
    if stem.endswith("-summary"):
        stem = stem[: -len("-summary")]
    parts = stem.split("-")
    if len(parts) >= 4 and parts[0].endswith("Z"):
        return "-".join(parts[3:])
    return stem


def _run_id(path: Path) -> str:
    return path.stem.split("-")[0]


def _result_record(result: Dict[str, Any], source_path: Path) -> Dict[str, Any]:
    test = result.get("testCase") or {}
    meta = test.get("metadata") or {}
    response = result.get("response") or {}
    response_meta = response.get("metadata") or {}
    urls = [item for item in (response_meta.get("source_urls") or []) if isinstance(item, str)]
    return {
        "query_id": meta.get("id") or test.get("description") or "unknown",
        "category": meta.get("category") or "unknown",
        "freshness_level": meta.get("freshness_level") or "unknown",
        "notes": meta.get("notes") or "",
        "query": (test.get("vars") or {}).get("query") or "",
        "lane": _lane(result.get("provider") or {}),
        "answer": (response.get("output") or "").strip(),
        "domains": _normalize_domains(response_meta),
        "urls": urls,
        "latency_ms": response.get("latencyMs") or result.get("latencyMs"),
        "source_count": int(response_meta.get("source_count") or 0),
        "source_artifact": str(source_path),
    }


def _write_score_csv(path: Path, rows: List[Dict[str, Any]], profile_id: str, run_id: str) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "profile_id": profile_id,
                    "lane": row["lane"],
                    "run_id": run_id,
                    "query_id": row["query_id"],
                    "usefulness_score": "",
                    "citation_quality_score": "",
                    "freshness_score": "",
                    "junk_domain_score": "",
                    "comments": "",
                }
            )


def _write_slice_markdown(path: Path, slice_name: str, grouped: Dict[str, List[Dict[str, Any]]]) -> None:
    lanes = sorted(grouped)
    query_ids = sorted({row["query_id"] for rows in grouped.values() for row in rows})
    by_lane_query = {lane: {row["query_id"]: row for row in rows} for lane, rows in grouped.items()}
    lines: List[str] = []
    lines.append(f"# Review Packet: {slice_name}")
    lines.append("")
    lines.append("Review rule: compare the same query across lanes, then score the CSV in this directory.")
    lines.append("")
    for query_id in query_ids:
        exemplar = next(by_lane_query[lane][query_id] for lane in lanes if query_id in by_lane_query[lane])
        lines.append(f"## {query_id}")
        lines.append("")
        lines.append(f"- Category: `{exemplar['category']}`")
        lines.append(f"- Freshness: `{exemplar['freshness_level']}`")
        lines.append(f"- Query: {exemplar['query']}")
        if exemplar["notes"]:
            lines.append(f"- Notes: {exemplar['notes']}")
        lines.append("")
        for lane in lanes:
            row = by_lane_query.get(lane, {}).get(query_id)
            if not row:
                continue
            lines.append(f"### {lane}")
            lines.append("")
            latency = f"{float(row['latency_ms']):.2f}" if row["latency_ms"] is not None else "n/a"
            lines.append(f"- Latency ms: {latency}")
            lines.append(f"- Source count: {row['source_count']}")
            lines.append(f"- Domains: {', '.join(f'`{domain}`' for domain in row['domains']) if row['domains'] else 'none'}")
            if row["urls"]:
                lines.append("- Source URLs:")
                for url in row["urls"][:8]:
                    lines.append(f"  - {url}")
            lines.append("")
            lines.append("Answer:")
            lines.append("")
            lines.append("```")
            lines.append(row["answer"] or "<empty output>")
            lines.append("```")
            lines.append("")
        lines.append("---")
        lines.append("")
    path.write_text("\n".join(lines))


def _copy_companion_summary(json_path: Path, summary_dir: Path) -> Path | None:
    summary_path = json_path.with_name(f"{json_path.stem}-summary.md")
    if not summary_path.exists():
        return None
    target = summary_dir / summary_path.name
    shutil.copy2(summary_path, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a consolidated review packet from saved web-search eval artifacts.")
    parser.add_argument("--input", action="append", required=True, help="Saved promptfoo JSON artifact")
    parser.add_argument("--output-dir", required=True, help="Review directory to create")
    parser.add_argument("--profile-id", default="baseline", help="Profile id to embed in generated review CSVs")
    args = parser.parse_args()

    inputs = [Path(item) for item in args.input]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_dir = output_dir / "summaries"
    summary_dir.mkdir(exist_ok=True)

    slice_groups: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    review_csv_inputs: List[Tuple[str, Path]] = []
    copied_summaries: List[Path] = []
    run_ids = []
    for path in inputs:
        run_ids.append(_run_id(path))
        copied = _copy_companion_summary(path, summary_dir)
        if copied is not None:
            copied_summaries.append(copied)
        slice_name = _slice_name(path)
        for result in _load_results(path):
            record = _result_record(result, path)
            slice_groups[slice_name][record["lane"]].append(record)

    packet_name = output_dir.name
    index_lines = [
        f"# Websearch Review Packet: {packet_name}",
        "",
        "Start here:",
        "1. Read the per-slice markdown files in this directory.",
        "2. Use the copied summary markdown files in `summaries/` for quick aggregate context.",
        "3. Fill in the score CSVs in this directory.",
        "4. Run `scripts/websearch_score_rollup.py` on the completed CSVs.",
        "",
        "## Included slices",
    ]

    for slice_name in sorted(slice_groups):
        slug = _safe_slug(slice_name)
        markdown_path = output_dir / f"{slug}.md"
        _write_slice_markdown(markdown_path, slice_name, slice_groups[slice_name])
        rows = [row for lane_rows in slice_groups[slice_name].values() for row in lane_rows]
        csv_path = output_dir / f"{slug}-review.csv"
        _write_score_csv(csv_path, rows, args.profile_id, run_ids[0] if run_ids else "unknown")
        review_csv_inputs.append((slice_name, csv_path))
        index_lines.append(f"- [{slice_name}]({markdown_path.name})")
        index_lines.append(f"  - score sheet: `{csv_path.name}`")

    index_lines.extend([
        "",
        "## Aggregate summaries",
    ])
    if copied_summaries:
        for path in copied_summaries:
            index_lines.append(f"- [summaries/{path.name}](summaries/{path.name})")
    else:
        index_lines.append("- none copied")

    index_lines.extend([
        "",
        "## Source artifacts",
    ])
    for path in inputs:
        index_lines.append(f"- `{path}`")

    index_lines.extend([
        "",
        "## Score rollup command",
        "```bash",
        "uv run python scripts/websearch_score_rollup.py \\",
    ])
    for _, csv_path in review_csv_inputs:
        index_lines.append(f"  --input {csv_path} \\")
    index_lines.extend([
        "  --baseline baseline:owui-fast \\",
        f"  --output {output_dir / 'lane-rollup.md'}",
        "```",
        "",
        "If `owui-fast` is not the baseline you want, change `--baseline` before running the rollup.",
    ])

    (output_dir / "README.md").write_text("\n".join(index_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
