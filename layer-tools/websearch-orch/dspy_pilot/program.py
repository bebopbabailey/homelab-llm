"""Backends for citation-fidelity pilot execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .metrics import score_case
from .models import Citation, CitationCase, ExpectedContract, ModelPrediction, parse_citations, parse_sources_json


class MockCitationBackend:
    """Deterministic backend for local metric/testing smoke checks."""

    name = "mock"

    def predict(self, case: CitationCase) -> ModelPrediction:
        citations: list[Citation] = []
        for source in case.retrieved_sources[: max(1, min(2, len(case.retrieved_sources)))]:
            citations.append(
                Citation(
                    source_id=source.source_id,
                    url=source.url,
                    claim_span=f"Grounded claim from source {source.source_id}: {source.title[:60]}",
                )
            )
        answer = " ".join(
            [
                "This is a deterministic mock answer used for metric validation.",
                f"Referenced sources: {', '.join(str(c.source_id) for c in citations if c.source_id)}.",
            ]
        )
        return ModelPrediction(answer_text=answer, citations=citations, raw={"backend": "mock"})

    def load(self, _path: Path) -> None:
        return None

    def save(self, _path: Path) -> None:
        return None

    def compile(
        self,
        _train_cases: list[CitationCase],
        _dev_cases: list[CitationCase],
        _optimizer_name: str,
        _num_trials: int,
    ) -> dict[str, Any]:
        return {
            "optimizer": "none",
            "compiled": False,
            "note": "mock backend does not compile",
        }


class DSPyCitationBackend:
    """DSPy-backed program with optional optimizer compile path."""

    name = "dspy"

    def __init__(
        self,
        model: str,
        api_base: str | None,
        api_key: str,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> None:
        try:
            import dspy
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "dspy is not installed. Install with: "
                "uv pip install --python layer-tools/websearch-orch/.venv/bin/python "
                "-r layer-tools/websearch-orch/requirements-dspy-pilot.txt"
            ) from exc

        self._dspy = dspy
        lm_kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if api_base:
            lm_kwargs["api_base"] = api_base
        if api_key:
            lm_kwargs["api_key"] = api_key
        self._lm = dspy.LM(**lm_kwargs)
        dspy.configure(lm=self._lm)
        self._program = self._build_program()

    def _build_program(self) -> Any:
        dspy = self._dspy

        class CitationResponseSignature(dspy.Signature):
            """Answer using only provided sources and return structured citations."""

            question = dspy.InputField(desc="User question.")
            retrieved_sources_json = dspy.InputField(
                desc="JSON array of sources with source_id, title, url, snippet."
            )
            answer_text = dspy.OutputField(desc="Grounded answer text.")
            citations_json = dspy.OutputField(
                desc="JSON array of citations. "
                "Each item: {source_id:int, url:str, claim_span:str}. "
                "No placeholders and source_id/url must come from retrieved_sources_json."
            )

        class CitationProgram(dspy.Module):
            def __init__(self) -> None:
                super().__init__()
                self.respond = dspy.ChainOfThought(CitationResponseSignature)

            def forward(self, question: str, retrieved_sources_json: str) -> Any:
                return self.respond(question=question, retrieved_sources_json=retrieved_sources_json)

        return CitationProgram()

    def _prediction_from_dspy(self, prediction: Any) -> ModelPrediction:
        answer_text = str(getattr(prediction, "answer_text", "")).strip()
        citations_payload = getattr(prediction, "citations_json", "[]")
        citations = parse_citations(citations_payload)
        raw = {
            "citations_json": citations_payload,
            "answer_text": answer_text,
        }
        return ModelPrediction(answer_text=answer_text, citations=citations, raw=raw)

    def predict(self, case: CitationCase) -> ModelPrediction:
        raw_prediction = self._program(
            question=case.question,
            retrieved_sources_json=case.prompt_sources_json(),
        )
        return self._prediction_from_dspy(raw_prediction)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(self._program, "save"):
            self._program.save(str(path))
            return
        raise RuntimeError("Current dspy program object does not support save().")

    def load(self, path: Path) -> None:
        if hasattr(self._program, "load"):
            self._program.load(str(path))
            return
        raise RuntimeError("Current dspy program object does not support load().")

    def _case_to_example(self, case: CitationCase) -> Any:
        dspy = self._dspy
        return dspy.Example(
            case_id=case.case_id,
            question=case.question,
            retrieved_sources_json=case.prompt_sources_json(),
            expected_json=json.dumps(case.expected.to_dict(), ensure_ascii=True),
        ).with_inputs("question", "retrieved_sources_json")

    def _score_prediction_from_example(self, example: Any, prediction: Any) -> float:
        expected_payload_raw = str(getattr(example, "expected_json", "{}"))
        try:
            expected_payload = json.loads(expected_payload_raw)
        except json.JSONDecodeError:
            expected_payload = {}
        expected = ExpectedContract.from_dict(expected_payload if isinstance(expected_payload, dict) else {})

        sources = parse_sources_json(str(getattr(example, "retrieved_sources_json", "[]")))
        case = CitationCase(
            case_id=str(getattr(example, "case_id", "compile-case")),
            question=str(getattr(example, "question", "")),
            retrieved_sources=sources,
            expected=expected,
        )
        model_prediction = self._prediction_from_dspy(prediction)
        return float(score_case(case, model_prediction).get("score", 0.0))

    def _build_optimizer(self, optimizer_name: str, num_trials: int) -> tuple[Any, str]:
        dspy = self._dspy
        teleprompt = getattr(dspy, "teleprompt", None)
        metric_fn = self._score_prediction_from_example

        if optimizer_name == "mipro":
            optimizer_cls = getattr(dspy, "MIPROv2", None)
            if optimizer_cls is None and teleprompt is not None:
                optimizer_cls = getattr(teleprompt, "MIPROv2", None)
            if optimizer_cls is None:
                raise RuntimeError("MIPROv2 optimizer was not found in installed dspy build.")
            for kwargs in (
                {"metric": metric_fn, "auto": "light", "num_threads": 1, "num_candidates": max(4, num_trials)},
                {"metric": metric_fn, "auto": "light"},
                {"metric": metric_fn},
            ):
                try:
                    return optimizer_cls(**kwargs), optimizer_cls.__name__
                except TypeError:
                    continue
            raise RuntimeError("Unable to construct MIPROv2 with this dspy version.")

        optimizer_cls = None
        if teleprompt is not None:
            optimizer_cls = getattr(teleprompt, "BootstrapFewShotWithRandomSearch", None)
        if optimizer_cls is None:
            raise RuntimeError("BootstrapFewShotWithRandomSearch optimizer was not found in dspy.teleprompt.")

        for kwargs in (
            {"metric": metric_fn, "num_candidate_programs": max(4, num_trials)},
            {"metric": metric_fn},
        ):
            try:
                return optimizer_cls(**kwargs), optimizer_cls.__name__
            except TypeError:
                continue
        raise RuntimeError("Unable to construct BootstrapFewShotWithRandomSearch with this dspy version.")

    @staticmethod
    def _compile_with_fallback(optimizer: Any, program: Any, trainset: list[Any], devset: list[Any]) -> Any:
        attempts = [
            {"student": program, "trainset": trainset, "valset": devset},
            {"student": program, "trainset": trainset},
            {"program": program, "trainset": trainset, "valset": devset},
            {"program": program, "trainset": trainset},
            {"module": program, "trainset": trainset, "valset": devset},
            {"module": program, "trainset": trainset},
        ]
        for kwargs in attempts:
            try:
                return optimizer.compile(**kwargs)
            except TypeError:
                continue
        raise RuntimeError("Optimizer compile() signature did not match known call patterns.")

    def compile(
        self,
        train_cases: list[CitationCase],
        dev_cases: list[CitationCase],
        optimizer_name: str,
        num_trials: int,
    ) -> dict[str, Any]:
        trainset = [self._case_to_example(case) for case in train_cases]
        devset = [self._case_to_example(case) for case in dev_cases]
        optimizer, optimizer_label = self._build_optimizer(optimizer_name=optimizer_name, num_trials=num_trials)
        compiled_program = self._compile_with_fallback(optimizer, self._program, trainset, devset)
        self._program = compiled_program
        return {
            "optimizer": optimizer_label,
            "compiled": True,
            "train_cases": len(train_cases),
            "dev_cases": len(dev_cases),
        }

