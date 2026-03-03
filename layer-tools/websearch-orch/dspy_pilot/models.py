"""Dataset and prediction contracts for DSPy citation-fidelity evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if not lines:
        return text
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _loads_json_maybe(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


@dataclass(frozen=True)
class SourceDoc:
    source_id: int
    title: str
    url: str
    snippet: str = ""
    content: str = ""

    @staticmethod
    def from_dict(payload: dict[str, Any], fallback_id: int) -> "SourceDoc":
        source_id = _to_int(
            payload.get("source_id", payload.get("id", payload.get("orch_source_id", fallback_id))),
            fallback_id,
        )
        return SourceDoc(
            source_id=max(1, source_id),
            title=str(payload.get("title", "")).strip(),
            url=str(payload.get("url", "")).strip(),
            snippet=str(payload.get("snippet", "")).strip(),
            content=str(payload.get("content", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
        }


@dataclass(frozen=True)
class ExpectedContract:
    must_include_source_ids: list[int] = field(default_factory=list)
    forbid_placeholder_urls: bool = True
    min_citations: int = 1

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "ExpectedContract":
        must_include = payload.get("must_include_source_ids", [])
        if not isinstance(must_include, list):
            must_include = []
        return ExpectedContract(
            must_include_source_ids=[_to_int(item) for item in must_include if _to_int(item) > 0],
            forbid_placeholder_urls=bool(payload.get("forbid_placeholder_urls", True)),
            min_citations=max(1, _to_int(payload.get("min_citations", 1), 1)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "must_include_source_ids": list(self.must_include_source_ids),
            "forbid_placeholder_urls": self.forbid_placeholder_urls,
            "min_citations": self.min_citations,
        }


@dataclass(frozen=True)
class CitationCase:
    case_id: str
    question: str
    retrieved_sources: list[SourceDoc]
    expected: ExpectedContract

    @staticmethod
    def from_dict(payload: dict[str, Any], fallback_id: int) -> "CitationCase":
        case_id = str(payload.get("id", payload.get("case_id", f"CASE-{fallback_id:03d}"))).strip()
        question = str(payload.get("question", "")).strip()

        raw_sources = payload.get("retrieved_sources", [])
        if not isinstance(raw_sources, list):
            raw_sources = []
        sources = [SourceDoc.from_dict(item, idx) for idx, item in enumerate(raw_sources, start=1)]

        expected_payload = payload.get("expected", {})
        if not isinstance(expected_payload, dict):
            expected_payload = {}
        expected = ExpectedContract.from_dict(expected_payload)
        return CitationCase(case_id=case_id, question=question, retrieved_sources=sources, expected=expected)

    def prompt_sources_json(self) -> str:
        compact = []
        for source in self.retrieved_sources:
            compact.append(
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "url": source.url,
                    "snippet": source.snippet,
                }
            )
        return json.dumps(compact, ensure_ascii=True)


@dataclass(frozen=True)
class Citation:
    source_id: int | None = None
    url: str = ""
    claim_span: str = ""

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "Citation":
        source_id_raw = payload.get("source_id")
        source_id = _to_int(source_id_raw, 0) if source_id_raw is not None else 0
        return Citation(
            source_id=source_id if source_id > 0 else None,
            url=str(payload.get("url", "")).strip(),
            claim_span=str(payload.get("claim_span", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "claim_span": self.claim_span,
        }


@dataclass(frozen=True)
class ModelPrediction:
    answer_text: str
    citations: list[Citation]
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_payload(answer_text: str, citations_payload: Any, raw: dict[str, Any] | None = None) -> "ModelPrediction":
        citations = parse_citations(citations_payload)
        return ModelPrediction(answer_text=answer_text.strip(), citations=citations, raw=raw or {})


def parse_citations(citations_payload: Any) -> list[Citation]:
    if citations_payload is None:
        return []
    payload: Any = citations_payload
    if isinstance(payload, str):
        stripped = _strip_code_fence(payload)
        payload = _loads_json_maybe(stripped, [])
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    citations: list[Citation] = []
    for item in payload:
        if isinstance(item, dict):
            citations.append(Citation.from_dict(item))
    return citations


def parse_sources_json(raw_sources_json: str) -> list[SourceDoc]:
    payload = _loads_json_maybe(raw_sources_json, [])
    if not isinstance(payload, list):
        return []
    return [SourceDoc.from_dict(item, idx) for idx, item in enumerate(payload, start=1) if isinstance(item, dict)]


def load_cases_jsonl(path: Path) -> list[CitationCase]:
    cases: list[CitationCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                continue
            cases.append(CitationCase.from_dict(payload, idx))
    return cases

