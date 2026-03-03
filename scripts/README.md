# scripts

Repository utility scripts.

## Current scripts
- `validate_handles.py` — validates `layer-gateway/registry/handles.jsonl`
  for schema, naming constraints, and duplicate tuple collisions.
- `openwebui_phase_a_baseline.py` — prints and scores the Open WebUI
  web-search baseline query pack.
- `dspy_citation_fidelity.py` — learning-first DSPy pilot for citation
  fidelity (contract print, dataset validate, eval, compile).

## Usage
- Prefer `uv run python scripts/validate_handles.py`.
- Default path target is `layer-gateway/registry/handles.jsonl`.
- DSPy pilot quickstart:
  - `uv run python scripts/dspy_citation_fidelity.py print-contract`
  - `uv run python scripts/dspy_citation_fidelity.py validate-dataset --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl`
  - `uv run python scripts/dspy_citation_fidelity.py eval --backend mock --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl`

## Canonical references
- Registry contract context: `docs/INTEGRATIONS.md`
- Truth hierarchy: `docs/_core/SOURCES_OF_TRUTH.md`
