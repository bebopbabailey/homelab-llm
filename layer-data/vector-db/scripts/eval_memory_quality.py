#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from eval_ir import calculate_ir_metrics, load_doc_judgments, stable_chunk_docno


GRADE_VALUES = {0, 1, 2}
SUPPORT = "support"
DISCONFIRM = "disconfirm"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid jsonl at {path}:{line_no}: {exc}") from exc
            if not isinstance(rec, dict):
                raise ValueError(f"invalid record type at {path}:{line_no}: expected object")
            rows.append(rec)
    return rows


def _post_json(url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {}
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
            return {"data": parsed}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} POST {url}: {text[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed POST {url}: {exc.reason}") from exc


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _normalize_signals(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = _normalize_text(value)
        if text:
            out.append(text)
    return out


def _case_polarity(case: dict[str, Any]) -> str:
    raw = _normalize_text(case.get("evidence_polarity", ""))
    if raw in {SUPPORT, DISCONFIRM}:
        return raw
    bucket = _normalize_text(case.get("bucket", ""))
    return DISCONFIRM if bucket == "negative_control" else SUPPORT


def _case_match_mode(case: dict[str, Any]) -> str:
    raw = _normalize_text(case.get("signal_match_mode", ""))
    return raw if raw in {"all", "min_k"} else "all"


def _case_signal_min_k(case: dict[str, Any], signal_count: int) -> int:
    if signal_count <= 0:
        return 0
    raw = case.get("signal_min_k", 0)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        value = signal_count if _case_match_mode(case) == "all" else min(2, signal_count)
    return max(1, min(value, signal_count))


def _case_meta(case: dict[str, Any]) -> dict[str, Any]:
    signals = _normalize_signals(case.get("must_have_signals", []))
    return {
        "bucket": str(case.get("bucket", "")),
        "polarity": _case_polarity(case),
        "match_mode": _case_match_mode(case),
        "signals": signals,
        "signal_min_k": _case_signal_min_k(case, len(signals)),
    }


def _hit_blob(hit: dict[str, Any]) -> str:
    parts = [
        hit.get("title", ""),
        hit.get("uri", ""),
        hit.get("text", ""),
    ]
    return _normalize_text("\n".join(str(part or "") for part in parts))


def _matched_signals(blob: str, signals: list[str]) -> list[str]:
    return [signal for signal in signals if signal in blob]


def _is_strong_match(meta: dict[str, Any], matched_count: int) -> bool:
    signals = meta.get("signals", [])
    if not signals:
        return False
    if meta.get("match_mode") == "all":
        return matched_count >= len(signals)
    return matched_count >= int(meta.get("signal_min_k", 0) or 0)


def _grade_hit(hit: dict[str, Any], case: dict[str, Any], mode: str) -> tuple[int, str]:
    meta = _case_meta(case)
    blob = _hit_blob(hit)
    matched = _matched_signals(blob, meta["signals"])
    matched_count = len(matched)
    strong = _is_strong_match(meta, matched_count)
    partial = matched_count > 0

    if mode == "strict_binary":
        grade = 2 if strong else 0
    else:
        if strong:
            grade = 2
        elif partial:
            grade = 1
        else:
            grade = 0

    note = (
        f"auto:{mode};polarity={meta['polarity']};policy={meta['match_mode']}:{meta['signal_min_k']};"
        f"matched={matched_count}/{len(meta['signals'])};signals={ '|'.join(matched) if matched else '-' }"
    )
    return grade, note


def _preview(text: str, limit: int = 220) -> str:
    one_line = " ".join((text or "").split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 3] + "..."


def _load_judgments(path: Path) -> dict[tuple[str, str], int]:
    return load_doc_judgments(path)


def _load_existing_grades(path: Path) -> dict[tuple[str, str], int]:
    if not path.exists():
        return {}
    try:
        return _load_judgments(path)
    except Exception:  # noqa: BLE001
        return {}


def _parse_grade_line(raw: str) -> list[int] | None:
    parts = raw.strip().split()
    if len(parts) != 10:
        return None
    out: list[int] = []
    for p in parts:
        if p not in {"0", "1", "2"}:
            return None
        out.append(int(p))
    return out


def _write_judgments_csv(path: Path, rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["run_id", "query_id", "rank", "chunk_id", "doc_id", "grade", "labeler", "notes"])
        for row in rows:
            writer.writerow(row)


def _rows_from_cases(
    cases: list[dict[str, Any]],
    run_id: str,
    seed: dict[tuple[str, str], int] | None = None,
) -> tuple[list[list[Any]], dict[tuple[str, int], int]]:
    rows: list[list[Any]] = []
    index: dict[tuple[str, int], int] = {}
    seeded = seed or {}
    for case in cases:
        qid = str(case.get("query_id", ""))
        hits = case.get("hits", []) if isinstance(case.get("hits", []), list) else []
        for rank in range(1, 11):
            hit = hits[rank - 1] if rank <= len(hits) else {}
            chunk_id = str(hit.get("chunk_id", "")).strip()
            key = (qid, chunk_id) if chunk_id else None
            grade = seeded.get(key, 0) if key else 0
            note = "seeded-existing" if key and key in seeded else "default-0"
            row = [
                run_id,
                qid,
                rank,
                chunk_id,
                hit.get("doc_id", ""),
                grade,
                "seed",
                note,
            ]
            index[(qid, rank)] = len(rows)
            rows.append(row)
    return rows, index


def _read_triage_ids(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ids = payload.get("flagged_query_ids", [])
    if not isinstance(ids, list):
        return []
    out: list[str] = []
    for value in ids:
        qid = str(value).strip()
        if qid:
            out.append(qid)
    return out


def _grades_for_case(case: dict[str, Any], labels: dict[tuple[str, str], int]) -> list[int]:
    qid = str(case.get("query_id", "")).strip()
    hits = case.get("hits", []) if isinstance(case.get("hits", []), list) else []
    grades: list[int] = []
    for rank in range(1, 11):
        hit = hits[rank - 1] if rank <= len(hits) else {}
        if hit:
            grade = labels.get((qid, stable_chunk_docno(hit)), 0)
        else:
            grade = 0
        grades.append(grade)
    return grades


def _bucket_hit_at_5(cases: list[dict[str, Any]], per_query_success: dict[str, float]) -> dict[str, float]:
    bucket_values: dict[str, list[float]] = {}
    for case in cases:
        bucket = str(case.get("bucket", ""))
        qid = str(case.get("query_id", ""))
        bucket_values.setdefault(bucket, []).append(float(per_query_success.get(qid, 0.0)))
    return {
        bucket: round(sum(values) / len(values), 4)
        for bucket, values in sorted(bucket_values.items())
        if values
    }


def _p95_latency_ms(cases: list[dict[str, Any]]) -> float:
    if not cases:
        return 0.0
    latency_vals = [float(case.get("latency_ms", 0.0) or 0.0) for case in cases]
    if len(latency_vals) == 1:
        return round(latency_vals[0], 3)
    return round(statistics.quantiles(latency_vals, n=100, method="inclusive")[94], 3)


def _metric_bundle(cases: list[dict[str, Any]], labels: dict[tuple[str, str], int]) -> tuple[dict[str, float], dict[str, float]]:
    base_metrics, per_query_success = calculate_ir_metrics(cases, labels)
    metrics = dict(base_metrics)
    metrics["p95_latency_ms"] = _p95_latency_ms(cases)
    return metrics, _bucket_hit_at_5(cases, per_query_success)


def _print_pack(pack_path: Path) -> int:
    pack = _read_jsonl(pack_path)
    print(f"# Vector DB Quality Query Pack\n# path={pack_path}\n# total={len(pack)}\n")
    for row in pack:
        print(f"[{row['query_id']}] ({row['bucket']}) {row['query']}")
    return 0


def _run_pack(args: argparse.Namespace) -> int:
    pack = _read_jsonl(Path(args.pack))
    out: list[dict[str, Any]] = []
    for row in pack:
        query = str(row.get("query", ""))
        if not query:
            continue
        started = time.perf_counter()
        response = _post_json(
            f"{args.api_base.rstrip('/')}/v1/memory/search",
            {
                "query": query,
                "top_k": args.top_k,
                "lexical_k": args.lexical_k,
                "vector_k": args.vector_k,
                "model_space": args.model_space,
            },
            timeout_seconds=args.timeout,
        )
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        hits = response.get("hits", [])
        if not isinstance(hits, list):
            hits = []
        meta = _case_meta(row)
        out.append(
            {
                "query_id": row.get("query_id", ""),
                "bucket": row.get("bucket", ""),
                "query": query,
                "answerable": bool(row.get("answerable", True)),
                "evidence_polarity": meta["polarity"],
                "must_have_signals": row.get("must_have_signals", []),
                "signal_match_mode": meta["match_mode"],
                "signal_min_k": meta["signal_min_k"],
                "notes": row.get("notes", ""),
                "latency_ms": latency_ms,
                "hit_count": len(hits),
                "hits": hits,
            }
        )

    report = {
        "run_id": args.run_id,
        "created_unix": int(time.time()),
        "api_base": args.api_base,
        "params": {
            "model_space": args.model_space,
            "top_k": args.top_k,
            "lexical_k": args.lexical_k,
            "vector_k": args.vector_k,
            "timeout": args.timeout,
        },
        "cases_total": len(out),
        "cases": out,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "cases_total": len(out)}, indent=2))
    return 0


def _autolabel(args: argparse.Namespace) -> int:
    run = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    cases = run.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise ValueError("run-json has no cases")

    if args.mode not in {"strict_binary", "conservative_graded"}:
        raise ValueError("unsupported autolabel mode")

    run_id = str(run.get("run_id", args.run_id or "RUN"))
    rows: list[list[Any]] = []
    grade_counts = {0: 0, 1: 0, 2: 0}

    for case in cases:
        qid = str(case.get("query_id", ""))
        hits = case.get("hits", []) if isinstance(case.get("hits", []), list) else []
        for rank in range(1, 11):
            hit = hits[rank - 1] if rank <= len(hits) else {}
            grade, note = _grade_hit(hit, case, args.mode)
            grade_counts[grade] += 1
            rows.append(
                [
                    run_id,
                    qid,
                    rank,
                    hit.get("chunk_id", ""),
                    hit.get("doc_id", ""),
                    grade,
                    args.labeler,
                    note,
                ]
            )

    out_path = Path(args.out_csv)
    _write_judgments_csv(out_path, rows)
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "rows": len(rows),
                "mode": args.mode,
                "graded_2": grade_counts[2],
                "graded_1": grade_counts[1],
                "graded_0": grade_counts[0],
            },
            indent=2,
        )
    )
    return 0


def _triage(args: argparse.Namespace) -> int:
    run = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    cases = run.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise ValueError("run-json has no cases")
    labels = _load_judgments(Path(args.judgments))

    flagged: list[dict[str, Any]] = []
    flagged_ids: list[str] = []
    for case in cases:
        qid = str(case.get("query_id", ""))
        polarity = _case_polarity(case)
        bucket = str(case.get("bucket", ""))
        grades = _grades_for_case(case, labels)
        top5 = grades[:5]
        reasons: list[str] = []

        if polarity == SUPPORT:
            if bucket == "exact_lookup" and (not top5 or top5[0] != 2):
                reasons.append("exact_lookup_top1_not_grade2")
            if not any(grade == 2 for grade in top5):
                reasons.append("no_grade2_top5")
            if any(grade == 1 for grade in top5) and not any(grade == 2 for grade in top5):
                reasons.append("only_partial_top5")
            first_two = next((idx for idx, grade in enumerate(grades, start=1) if grade == 2), None)
            if first_two is not None and first_two > 3 and grades[0] == 0:
                reasons.append("weak_top1_late_first_grade2")
        else:
            if not any(grade == 2 for grade in top5):
                reasons.append("no_disconfirm_grade2_top5")
            if any(grade == 1 for grade in top5) and not any(grade == 2 for grade in top5):
                reasons.append("only_partial_disconfirm_top5")

        if reasons:
            flagged_ids.append(qid)
            hits = case.get("hits", []) if isinstance(case.get("hits", []), list) else []
            flagged.append(
                {
                    "query_id": qid,
                    "bucket": bucket,
                    "evidence_polarity": polarity,
                    "reasons": reasons,
                    "top5": [
                        {
                            "rank": rank,
                            "grade": grades[rank - 1],
                            "title": str((hits[rank - 1] if rank <= len(hits) else {}).get("title", "")),
                            "uri": str((hits[rank - 1] if rank <= len(hits) else {}).get("uri", "")),
                        }
                        for rank in range(1, 6)
                    ],
                }
            )

    out = {
        "ok": True,
        "run_id": run.get("run_id", ""),
        "flagged_count": len(flagged),
        "flagged_query_ids": flagged_ids,
        "flags": flagged,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "flagged_count": len(flagged)}, indent=2))
    return 0


def _label(args: argparse.Namespace) -> int:
    run = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    cases = run.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise ValueError("run-json has no cases")

    out_path = Path(args.out_csv)
    seed_path = Path(args.seed_judgments) if args.seed_judgments else None
    if args.triage_json and seed_path is None:
        raise ValueError("--triage-json requires --seed-judgments so unreviewed rows are preserved")

    existing = _load_existing_grades(seed_path) if seed_path else _load_existing_grades(out_path)
    run_id = str(run.get("run_id", args.run_id or "RUN"))
    rows, row_index = _rows_from_cases(cases, run_id, existing)

    case_map = {str(case.get("query_id", "")): case for case in cases}
    if args.triage_json:
        qids = _read_triage_ids(Path(args.triage_json))
        review_cases = [case_map[qid] for qid in qids if qid in case_map]
        if not review_cases:
            _write_judgments_csv(out_path, rows)
            print(json.dumps({"ok": True, "out": str(out_path), "saved_rows": len(rows), "quit_early": False, "reviewed_cases": 0}, indent=2))
            return 0
    else:
        review_cases = cases

    print("\nInteractive grader")
    print("Enter grades for ranks 1..10 as: 2 1 0 0 0 0 0 0 0 0")
    print("Commands: 's' = keep existing/skip, 'q' = save and quit\n")

    for idx, case in enumerate(review_cases, start=1):
        qid = str(case.get("query_id", ""))
        query = str(case.get("query", ""))
        polarity = _case_polarity(case)
        signals = case.get("must_have_signals", [])
        hits = case.get("hits", []) if isinstance(case.get("hits", []), list) else []

        print("=" * 88)
        print(f"[{idx}/{len(review_cases)}] {qid}")
        print(f"Query: {query}")
        print(f"Polarity: {polarity}")
        print(f"Signals: {signals}")
        print("-" * 88)

        for rank in range(1, 11):
            hit = hits[rank - 1] if rank <= len(hits) else {}
            title = str(hit.get("title", ""))
            uri = str(hit.get("uri", ""))
            text = _preview(str(hit.get("text", "")))
            existing_grade = rows[row_index[(qid, rank)]][5]
            print(f"[{rank}] chunk={hit.get('chunk_id', '')} doc={hit.get('doc_id', '')} existing={existing_grade}")
            if title:
                print(f"    title: {title}")
            if uri:
                print(f"    uri:   {uri}")
            if text:
                print(f"    text:  {text}")

        while True:
            raw = input("\nGrades (10 nums) / s / q: ").strip().lower()
            if raw == "q":
                _write_judgments_csv(out_path, rows)
                print(json.dumps({"ok": True, "out": str(out_path), "saved_rows": len(rows), "quit_early": True}, indent=2))
                return 0
            if raw == "s":
                break

            grades = _parse_grade_line(raw)
            if grades is None:
                print("Invalid input. Enter exactly 10 values of 0/1/2, or 's', or 'q'.")
                continue

            for rank, grade in enumerate(grades, start=1):
                row = rows[row_index[(qid, rank)]]
                row[5] = grade
                row[6] = args.labeler
                row[7] = "manual-interactive"
            break

        print()

    _write_judgments_csv(out_path, rows)
    print(json.dumps({"ok": True, "out": str(out_path), "saved_rows": len(rows), "quit_early": False, "reviewed_cases": len(review_cases)}, indent=2))
    return 0


def _score(args: argparse.Namespace) -> int:
    run = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    cases = run.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise ValueError("run-json has no cases")
    labels = _load_judgments(Path(args.judgments))

    metrics_all, bucket_all = _metric_bundle(cases, labels)
    support_cases = [case for case in cases if _case_polarity(case) == SUPPORT]
    disconfirm_cases = [case for case in cases if _case_polarity(case) == DISCONFIRM]
    metrics_support, bucket_support = _metric_bundle(support_cases, labels)
    metrics_disconfirm, bucket_disconfirm = _metric_bundle(disconfirm_cases, labels)

    support_bucket_floor = all(value >= 0.75 for value in bucket_support.values()) if bucket_support else True
    disconfirm_hit = metrics_disconfirm["hit_at_5"] if disconfirm_cases else 1.0
    p95_latency = metrics_all["p95_latency_ms"]

    summary = {
        "run_id": run.get("run_id", ""),
        "input": {
            "run_json": args.run_json,
            "judgments": args.judgments,
        },
        "params": run.get("params", {}),
        "case_counts": {
            "total": len(cases),
            "support": len(support_cases),
            "disconfirm": len(disconfirm_cases),
        },
        "metrics": metrics_all,
        "metrics_legacy": metrics_all,
        "metrics_support": metrics_support,
        "metrics_disconfirm": metrics_disconfirm,
        "bucket_hit_at_5": bucket_all,
        "bucket_hit_at_5_support": bucket_support,
        "bucket_hit_at_5_disconfirm": bucket_disconfirm,
        "diagnostics": {
            "bad_hit_rate_at_5": metrics_all["bad_hit_rate_at_5"],
        },
        "gates": {
            "hit_at_5": metrics_support["hit_at_5"] >= 0.85,
            "mrr_at_10": metrics_support["mrr_at_10"] >= 0.65,
            "ndcg_at_10": metrics_support["ndcg_at_10"] >= 0.70,
            "bucket_floor": support_bucket_floor,
            "disconfirm_hit_at_5": disconfirm_hit >= 0.67,
            "p95_latency_ms": p95_latency <= 800.0,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, indent=2))
    return 0


def _compare(args: argparse.Namespace) -> int:
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    cand = json.loads(Path(args.candidate).read_text(encoding="utf-8"))

    bm_support = base.get("metrics_support") or base.get("metrics", {})
    cm_support = cand.get("metrics_support") or cand.get("metrics", {})
    bm_disconfirm = base.get("metrics_disconfirm", {})
    cm_disconfirm = cand.get("metrics_disconfirm", {})

    def _d(bm: dict[str, Any], cm: dict[str, Any], key: str) -> float:
        return round(float(cm.get(key, 0.0)) - float(bm.get(key, 0.0)), 4)

    report = {
        "baseline": args.baseline,
        "candidate": args.candidate,
        "delta": {
            "hit_at_5": _d(bm_support, cm_support, "hit_at_5"),
            "mrr_at_10": _d(bm_support, cm_support, "mrr_at_10"),
            "ndcg_at_10": _d(bm_support, cm_support, "ndcg_at_10"),
            "bad_hit_rate_at_5": _d(base.get("metrics", {}), cand.get("metrics", {}), "bad_hit_rate_at_5"),
            "p95_latency_ms": _d(base.get("metrics", {}), cand.get("metrics", {}), "p95_latency_ms"),
            "disconfirm_hit_at_5": _d(bm_disconfirm, cm_disconfirm, "hit_at_5"),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vector DB retrieval quality evaluation helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_print = sub.add_parser("print-pack", help="Print query pack")
    p_print.add_argument("--pack", required=True)

    p_run = sub.add_parser("run-pack", help="Run query pack against memory API")
    p_run.add_argument("--pack", required=True)
    p_run.add_argument("--api-base", default="http://127.0.0.1:55440")
    p_run.add_argument("--model-space", choices=["qwen", "mxbai"], default="qwen")
    p_run.add_argument("--top-k", type=int, default=10)
    p_run.add_argument("--lexical-k", type=int, default=30)
    p_run.add_argument("--vector-k", type=int, default=30)
    p_run.add_argument("--timeout", type=int, default=20)
    p_run.add_argument("--run-id", required=True)
    p_run.add_argument("--out", required=True)

    p_auto = sub.add_parser("autolabel", help="Auto-label a run JSON using signal rules")
    p_auto.add_argument("--run-json", required=True)
    p_auto.add_argument("--out-csv", required=True)
    p_auto.add_argument("--mode", choices=["strict_binary", "conservative_graded"], default="conservative_graded")
    p_auto.add_argument("--labeler", default="codex-auto")
    p_auto.add_argument("--run-id", default=None)

    p_triage = sub.add_parser("triage", help="Flag only the cases that need human review")
    p_triage.add_argument("--run-json", required=True)
    p_triage.add_argument("--judgments", required=True)
    p_triage.add_argument("--out", required=True)

    p_score = sub.add_parser("score", help="Score judged run output")
    p_score.add_argument("--run-json", required=True)
    p_score.add_argument("--judgments", required=True)
    p_score.add_argument("--out", required=True)

    p_compare = sub.add_parser("compare", help="Compare two score summaries")
    p_compare.add_argument("--baseline", required=True)
    p_compare.add_argument("--candidate", required=True)
    p_compare.add_argument("--out", required=True)

    p_label = sub.add_parser("label", help="Interactive 0/1/2 grader for a run JSON")
    p_label.add_argument("--run-json", required=True)
    p_label.add_argument("--out-csv", required=True)
    p_label.add_argument("--labeler", default="human")
    p_label.add_argument("--run-id", default=None)
    p_label.add_argument("--seed-judgments", default=None)
    p_label.add_argument("--triage-json", default=None)

    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.cmd == "print-pack":
            return _print_pack(Path(args.pack))
        if args.cmd == "run-pack":
            return _run_pack(args)
        if args.cmd == "autolabel":
            return _autolabel(args)
        if args.cmd == "triage":
            return _triage(args)
        if args.cmd == "score":
            return _score(args)
        if args.cmd == "compare":
            return _compare(args)
        if args.cmd == "label":
            return _label(args)
        raise ValueError(f"unknown cmd: {args.cmd}")
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
