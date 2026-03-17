#!/usr/bin/env python3
"""Aggregate manual web-search scoring CSVs into a markdown decision summary."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Tuple

SCORE_FIELDS = (
    "usefulness_score",
    "citation_quality_score",
    "freshness_score",
    "junk_domain_score",
)


def _read_rows(path: Path) -> List[Dict[str, object]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {
            "profile_id",
            "lane",
            "run_id",
            "query_id",
            *SCORE_FIELDS,
            "comments",
        }
        if set(reader.fieldnames or []) != expected:
            raise SystemExit(f"unexpected CSV columns in {path}: {reader.fieldnames}")
        rows: List[Dict[str, object]] = []
        for raw in reader:
            row = dict(raw)
            for field in SCORE_FIELDS:
                value = (raw.get(field) or "").strip()
                if not value:
                    raise SystemExit(f"missing {field} in {path} for query {raw.get('query_id')}")
                score = int(value)
                if score < 1 or score > 5:
                    raise SystemExit(f"invalid {field}={score} in {path} for query {raw.get('query_id')}")
                row[field] = score
            rows.append(row)
        return rows


def _group_key(row: Dict[str, object]) -> Tuple[str, str]:
    return str(row["profile_id"]), str(row["lane"])


def _avg(rows: Iterable[Dict[str, object]], field: str) -> float:
    values = [int(row[field]) for row in rows]
    return mean(values) if values else 0.0


def _format_delta(value: float) -> str:
    return f"{value:+.2f}"


def _render(inputs: List[Path], rows: List[Dict[str, object]], baseline: Tuple[str, str] | None) -> str:
    grouped: Dict[Tuple[str, str], List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[_group_key(row)].append(row)

    lines: List[str] = []
    lines.append("# Websearch Manual Score Rollup")
    lines.append("")
    lines.append("## Inputs")
    for path in inputs:
        lines.append(f"- `{path}`")
    lines.append("")
    lines.append("## Groups")
    lines.append("| profile | lane | rows | usefulness | citation | freshness | junk-domain |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for (profile_id, lane) in sorted(grouped):
        group = grouped[(profile_id, lane)]
        lines.append(
            f"| {profile_id} | {lane} | {len(group)} | "
            f"{_avg(group, 'usefulness_score'):.2f} | "
            f"{_avg(group, 'citation_quality_score'):.2f} | "
            f"{_avg(group, 'freshness_score'):.2f} | "
            f"{_avg(group, 'junk_domain_score'):.2f} |"
        )
    if baseline:
        base_rows = grouped.get(baseline)
        lines.append("")
        lines.append("## Baseline Deltas")
        if not base_rows:
            lines.append(f"- baseline `{baseline[0]}:{baseline[1]}` not found in inputs")
        else:
            base_scores = {field: _avg(base_rows, field) for field in SCORE_FIELDS}
            lines.append(f"- baseline: `{baseline[0]}:{baseline[1]}`")
            lines.append("")
            lines.append("| profile | lane | usefulness Δ | citation Δ | freshness Δ | junk-domain Δ |")
            lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
            for (profile_id, lane) in sorted(grouped):
                if (profile_id, lane) == baseline:
                    continue
                group = grouped[(profile_id, lane)]
                deltas = {
                    field: _avg(group, field) - base_scores[field]
                    for field in SCORE_FIELDS
                }
                lines.append(
                    f"| {profile_id} | {lane} | "
                    f"{_format_delta(deltas['usefulness_score'])} | "
                    f"{_format_delta(deltas['citation_quality_score'])} | "
                    f"{_format_delta(deltas['freshness_score'])} | "
                    f"{_format_delta(deltas['junk_domain_score'])} |"
                )
            lines.append("")
            lines.append("## Decision Note")
            lines.append("- This rollup is score-only.")
            lines.append("- Final promotion still requires the matching promptfoo summary to confirm assertions, blocked-domain hits, zero-source cases, and latency gates.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Roll up manual web-search scoring CSVs.")
    parser.add_argument("--input", action="append", required=True, help="Manual scoring CSV file")
    parser.add_argument("--baseline", help="Baseline in profile_id:lane form")
    parser.add_argument("--output", help="Optional markdown output path")
    args = parser.parse_args()

    inputs = [Path(item) for item in args.input]
    rows: List[Dict[str, object]] = []
    for path in inputs:
        rows.extend(_read_rows(path))

    baseline = None
    if args.baseline:
        if ":" not in args.baseline:
            raise SystemExit("--baseline must use profile_id:lane form")
        profile_id, lane = args.baseline.split(":", 1)
        baseline = (profile_id, lane)

    output = _render(inputs, rows, baseline)
    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
