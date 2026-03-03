"""DSPy citation-fidelity pilot helpers for websearch-orch."""

from .metrics import aggregate_scores, score_case
from .models import Citation, CitationCase, ModelPrediction, load_cases_jsonl
from .program import DSPyCitationBackend, MockCitationBackend

__all__ = [
    "Citation",
    "CitationCase",
    "DSPyCitationBackend",
    "MockCitationBackend",
    "ModelPrediction",
    "aggregate_scores",
    "load_cases_jsonl",
    "score_case",
]
