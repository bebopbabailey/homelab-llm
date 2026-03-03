#!/usr/bin/env python3
"""DSPy learning-first pilot for citation fidelity.

This script intentionally supports a deterministic `mock` backend so metrics and
contracts can be tested without requiring an LLM call. Use `dspy` backend for
real optimization runs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBSEARCH_ORCH_ROOT = REPO_ROOT / "layer-tools" / "websearch-orch"
if str(WEBSEARCH_ORCH_ROOT) not in sys.path:
    sys.path.insert(0, str(WEBSEARCH_ORCH_ROOT))

from dspy_pilot import (  # noqa: E402
    DSPyCitationBackend,
    MockCitationBackend,
    aggregate_scores,
    load_cases_jsonl,
    score_case,
)

DEFAULT_SAMPLE_DATASET = WEBSEARCH_ORCH_ROOT / "dspy_pilot" / "data" / "citation_fidelity.sample.jsonl"
DEFAULT_SCHEMA_PATH = WEBSEARCH_ORCH_ROOT / "dspy_pilot" / "schemas" / "citation_response.schema.json"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")


def _load_dataset(path: Path) -> list[Any]:
    cases = load_cases_jsonl(path)
    if not cases:
        raise RuntimeError(f"Dataset is empty: {path}")
    return cases


def _backend_from_args(args: argparse.Namespace) -> Any:
    if args.backend == "mock":
        return MockCitationBackend()
    api_key = os.getenv(args.api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing API key env var: {args.api_key_env}")
    return DSPyCitationBackend(
        model=args.model,
        api_base=args.api_base,
        api_key=api_key,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )


def _evaluate_cases(cases: list[Any], backend: Any, max_cases: int | None = None) -> dict[str, Any]:
    selected = cases[:max_cases] if max_cases and max_cases > 0 else cases
    started = time.time()
    per_case: list[dict[str, Any]] = []

    for case in selected:
        prediction = backend.predict(case)
        scored = score_case(case, prediction)
        per_case.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected": asdict(case.expected),
                "prediction": {
                    "answer_text": prediction.answer_text,
                    "citations": [citation.to_dict() for citation in prediction.citations],
                },
                "score": scored,
            }
        )

    elapsed = round(time.time() - started, 3)
    summary = aggregate_scores([entry["score"] for entry in per_case])
    summary["elapsed_seconds"] = elapsed
    return {"summary": summary, "per_case": per_case}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def cmd_print_contract(_args: argparse.Namespace) -> int:
    print("# DSPy Citation-Fidelity Contract")
    print("")
    print("Input dataset JSONL fields per case:")
    print("- `id` (string)")
    print("- `question` (string)")
    print("- `retrieved_sources` (array of `{source_id,title,url,snippet}`)")
    print("- `expected` (object)")
    print("  - `must_include_source_ids` (array[int])")
    print("  - `forbid_placeholder_urls` (bool, default true)")
    print("  - `min_citations` (int, default 1)")
    print("")
    print("Scoring rubric:")
    print("- citation_validity: 45%")
    print("- citation_specificity: 30%")
    print("- groundedness_proxy: 20%")
    print("- placeholder penalty: 5% + hard fail if placeholders are forbidden")
    print("")
    print(f"Schema reference: {DEFAULT_SCHEMA_PATH}")
    return 0


def cmd_validate_dataset(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset).resolve()
    cases = _load_dataset(dataset)
    print(
        json.dumps(
            {
                "dataset": str(dataset),
                "cases_total": len(cases),
                "first_case_id": cases[0].case_id if cases else None,
                "first_case_source_count": len(cases[0].retrieved_sources) if cases else 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def cmd_init_sample(args: argparse.Namespace) -> int:
    destination = Path(args.output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(DEFAULT_SAMPLE_DATASET.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote sample dataset to {destination}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset).resolve()
    report_out = Path(args.report_out).resolve() if args.report_out else Path(f"/tmp/dspy-citation-eval-{_utc_timestamp()}.json")
    cases = _load_dataset(dataset)

    backend = _backend_from_args(args)
    if args.compiled_program:
        backend.load(Path(args.compiled_program).resolve())

    evaluated = _evaluate_cases(cases=cases, backend=backend, max_cases=args.max_cases)
    payload = {
        "run_type": "eval",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": args.backend,
        "dataset": str(dataset),
        "model": args.model if args.backend == "dspy" else "mock",
        "api_base": args.api_base if args.backend == "dspy" else None,
        "compiled_program": str(Path(args.compiled_program).resolve()) if args.compiled_program else None,
        **evaluated,
    }
    _write_json(report_out, payload)
    print(json.dumps({"report_out": str(report_out), "summary": payload["summary"]}, indent=2, sort_keys=True))
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    if args.backend != "dspy":
        raise RuntimeError("compile requires --backend dspy")

    train_dataset = Path(args.train_dataset).resolve()
    dev_dataset = Path(args.dev_dataset).resolve()
    artifact_dir = Path(args.artifact_dir).resolve() if args.artifact_dir else Path(f"/tmp/dspy-citation-artifacts-{_utc_timestamp()}")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    train_cases = _load_dataset(train_dataset)
    dev_cases = _load_dataset(dev_dataset)
    backend = _backend_from_args(args)
    compile_meta = backend.compile(
        train_cases=train_cases,
        dev_cases=dev_cases,
        optimizer_name=args.optimizer,
        num_trials=args.num_trials,
    )

    compiled_program_path = artifact_dir / "compiled_program.json"
    backend.save(compiled_program_path)

    eval_result = _evaluate_cases(cases=dev_cases, backend=backend, max_cases=args.max_cases)
    report_path = artifact_dir / "compile_report.json"
    payload = {
        "run_type": "compile",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": args.backend,
        "model": args.model,
        "api_base": args.api_base,
        "train_dataset": str(train_dataset),
        "dev_dataset": str(dev_dataset),
        "compiled_program_path": str(compiled_program_path),
        "compile_meta": compile_meta,
        **eval_result,
    }
    _write_json(report_path, payload)
    print(
        json.dumps(
            {
                "compiled_program_path": str(compiled_program_path),
                "report_out": str(report_path),
                "summary": payload["summary"],
                "compile_meta": compile_meta,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DSPy citation-fidelity pilot driver")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_contract = sub.add_parser("print-contract", help="Print dataset + metric contract")
    p_contract.set_defaults(func=cmd_print_contract)

    p_validate = sub.add_parser("validate-dataset", help="Validate dataset shape and counts")
    p_validate.add_argument("--dataset", default=str(DEFAULT_SAMPLE_DATASET))
    p_validate.set_defaults(func=cmd_validate_dataset)

    p_init = sub.add_parser("init-sample", help="Copy bundled sample dataset to a target path")
    p_init.add_argument("--output", required=True)
    p_init.set_defaults(func=cmd_init_sample)

    for name, help_text in (
        ("eval", "Run citation-fidelity evaluation"),
        ("compile", "Compile DSPy program and evaluate on dev set"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        if name == "eval":
            cmd.add_argument("--dataset", default=str(DEFAULT_SAMPLE_DATASET))
            cmd.add_argument("--report-out")
            cmd.add_argument("--compiled-program")
        else:
            cmd.add_argument("--train-dataset", default=str(DEFAULT_SAMPLE_DATASET))
            cmd.add_argument("--dev-dataset", default=str(DEFAULT_SAMPLE_DATASET))
            cmd.add_argument("--artifact-dir")
            cmd.add_argument("--optimizer", choices=("bootstrap", "mipro"), default="bootstrap")
            cmd.add_argument("--num-trials", type=int, default=8)

        if name == "compile":
            cmd.add_argument("--backend", choices=("dspy",), default="dspy")
        else:
            cmd.add_argument("--backend", choices=("mock", "dspy"), default="mock")
        cmd.add_argument("--model", default="openai/fast")
        cmd.add_argument("--api-base", default="http://127.0.0.1:4000/v1")
        cmd.add_argument("--api-key-env", default="LITELLM_MASTER_KEY")
        cmd.add_argument("--temperature", type=float, default=0.0)
        cmd.add_argument("--max-tokens", type=int, default=800)
        cmd.add_argument("--max-cases", type=int)
        cmd.set_defaults(func=cmd_eval if name == "eval" else cmd_compile)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc), "command": args.cmd}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
