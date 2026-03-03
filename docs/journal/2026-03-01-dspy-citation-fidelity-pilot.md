# 2026-03-01 - DSPy citation-fidelity pilot scaffold (learning-first)

## Summary
Implemented a learning-first DSPy pilot scaffold for web-search citation quality without changing live `websearch-orch` runtime request handling.

The pilot adds:
- a dataset contract and starter JSONL set,
- a citation-fidelity metric rubric with weighted scoring,
- a CLI for validate/eval/compile loops (`mock` and `dspy` backends),
- and operator docs for reproducible local runs.

## What changed
- Added optional DSPy dependencies:
  - `layer-tools/websearch-orch/requirements-dspy-pilot.txt`
- Added pilot package:
  - `layer-tools/websearch-orch/dspy_pilot/__init__.py`
  - `layer-tools/websearch-orch/dspy_pilot/models.py`
  - `layer-tools/websearch-orch/dspy_pilot/metrics.py`
  - `layer-tools/websearch-orch/dspy_pilot/program.py`
  - `layer-tools/websearch-orch/dspy_pilot/README.md`
  - `layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl`
  - `layer-tools/websearch-orch/dspy_pilot/schemas/citation_response.schema.json`
- Added CLI driver:
  - `scripts/dspy_citation_fidelity.py`
- Updated docs:
  - `scripts/README.md`
  - `layer-tools/websearch-orch/RUNBOOK.md`
  - `docs/foundation/testing.md`
  - `NOW.md`
  - `BACKLOG.md`
  - `docs/journal/index.md`

## Verification (FAST)
- `uv run python -m py_compile scripts/dspy_citation_fidelity.py layer-tools/websearch-orch/dspy_pilot/__init__.py layer-tools/websearch-orch/dspy_pilot/models.py layer-tools/websearch-orch/dspy_pilot/metrics.py layer-tools/websearch-orch/dspy_pilot/program.py`
- `uv run python scripts/dspy_citation_fidelity.py validate-dataset --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl`
- `uv run python scripts/dspy_citation_fidelity.py eval --backend mock --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl --report-out /tmp/dspy_citation_report.json`
- `uv run python scripts/dspy_citation_fidelity.py print-contract`

## Notes
- `layer-tools/websearch-orch/CONSTRAINTS.md` and `SERVICE_SPEC.md` remain absent; continued with least-risk interpretation and runtime-isolation (no live request-path changes).
- DSPy compile/eval against a real model requires a configured API key env var at run time.
