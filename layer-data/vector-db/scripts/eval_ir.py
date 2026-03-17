from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import ir_measures
from ir_measures import P, RR, Success, nDCG

HIT_AT_5 = Success(rel=2, judged_only=False) @ 5
MRR_AT_10 = RR(rel=2, judged_only=False) @ 10
NDCG_AT_10 = nDCG(gains={0: 0, 1: 1, 2: 3}, dcg="log2", judged_only=False) @ 10
NOT_BAD_P_AT_5 = P(rel=1, judged_only=False) @ 5
CANONICAL_MEASURES = [HIT_AT_5, MRR_AT_10, NDCG_AT_10, NOT_BAD_P_AT_5]


def verify_ir_backend() -> None:
    try:
        qrels = [ir_measures.Qrel("q0", "d0", 2)]
        run = [ir_measures.ScoredDoc("q0", "d0", 1.0)]
        ir_measures.calc_aggregate(CANONICAL_MEASURES, qrels, run)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "ir-measures canonical provider check failed; verify ir-measures==0.4.3 "
            "and pytrec-eval-terrier==0.5.10 are installed for this service environment"
        ) from exc


def stable_chunk_docno(record: dict[str, Any]) -> str:
    raw = record.get("chunk_id", "")
    value = str(raw).strip()
    if not value:
        raise ValueError(f"missing chunk_id in eval artifact: {record}")
    return value


def load_doc_judgments(path: Path) -> dict[tuple[str, str], int]:
    labels: dict[tuple[str, str], int] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"query_id", "chunk_id", "grade"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"judgment csv missing required columns: {sorted(required)}")
        for row in reader:
            query_id = str(row.get("query_id", "")).strip()
            if not query_id:
                continue
            raw_docno = str(row.get("chunk_id", "")).strip()
            if not raw_docno:
                continue
            docno = raw_docno
            try:
                grade = int(str(row.get("grade", "")).strip())
            except ValueError:
                continue
            if grade not in {0, 1, 2}:
                continue
            key = (query_id, docno)
            if key in labels and labels[key] != grade:
                raise ValueError(f"conflicting grades for query_id={query_id} chunk_id={docno}")
            labels[key] = grade
    return labels


def judgments_to_qrels(cases: list[dict[str, Any]], labels: dict[tuple[str, str], int]) -> list[ir_measures.Qrel]:
    qids = {str(case.get("query_id", "")).strip() for case in cases}
    return [
        ir_measures.Qrel(query_id, docno, grade)
        for (query_id, docno), grade in sorted(labels.items())
        if query_id in qids
    ]


def cases_to_scored_docs(cases: list[dict[str, Any]]) -> list[ir_measures.ScoredDoc]:
    docs: list[ir_measures.ScoredDoc] = []
    seen: set[tuple[str, str]] = set()
    for case in cases:
        query_id = str(case.get("query_id", "")).strip()
        hits = case.get("hits", []) if isinstance(case.get("hits", []), list) else []
        for rank, hit in enumerate(hits, start=1):
            docno = stable_chunk_docno(hit)
            key = (query_id, docno)
            if key in seen:
                raise ValueError(f"duplicate chunk_id in run for query_id={query_id} chunk_id={docno}")
            seen.add(key)
            raw_score = hit.get("rrf_score", None)
            score = float(raw_score) if isinstance(raw_score, (int, float)) else (1.0 / rank)
            docs.append(ir_measures.ScoredDoc(query_id, docno, score))
    return docs


def calculate_ir_metrics(cases: list[dict[str, Any]], labels: dict[tuple[str, str], int]) -> tuple[dict[str, float], dict[str, float]]:
    if not cases:
        return {
            "hit_at_5": 0.0,
            "mrr_at_10": 0.0,
            "ndcg_at_10": 0.0,
            "bad_hit_rate_at_5": 0.0,
        }, {}

    verify_ir_backend()
    qrels = judgments_to_qrels(cases, labels)
    run_docs = cases_to_scored_docs(cases)
    aggregate = ir_measures.calc_aggregate(CANONICAL_MEASURES, qrels, run_docs)
    per_query_success = {
        metric.query_id: float(metric.value)
        for metric in ir_measures.iter_calc([HIT_AT_5], qrels, run_docs)
    }

    metrics = {
        "hit_at_5": round(float(aggregate[HIT_AT_5]), 4),
        "mrr_at_10": round(float(aggregate[MRR_AT_10]), 4),
        "ndcg_at_10": round(float(aggregate[NDCG_AT_10]), 4),
        "bad_hit_rate_at_5": round(1.0 - float(aggregate[NOT_BAD_P_AT_5]), 4),
    }
    return metrics, per_query_success


def write_trec_qrels(qrels: list[ir_measures.Qrel], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(f"{q.query_id} 0 {q.doc_id} {q.relevance}" for q in qrels) + "\n",
        encoding="utf-8",
    )


def write_trec_run(scored_docs: list[ir_measures.ScoredDoc], out_path: Path, run_id: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[ir_measures.ScoredDoc]] = {}
    for doc in scored_docs:
        grouped.setdefault(doc.query_id, []).append(doc)
    lines: list[str] = []
    for query_id, docs in sorted(grouped.items()):
        ranked = sorted(docs, key=lambda item: item.score, reverse=True)
        for rank, doc in enumerate(ranked, start=1):
            lines.append(f"{query_id} Q0 {doc.doc_id} {rank} {doc.score} {run_id}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_run_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
