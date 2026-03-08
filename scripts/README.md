# scripts

Repository utility scripts.

## Current scripts
- `validate_handles.py` — validates `layer-gateway/registry/handles.jsonl`
  for schema, naming constraints, and duplicate tuple collisions.
- `docs_contract_audit.py` — audits service-level docs contract completeness
  (`README`, `SERVICE_SPEC`, `ARCHITECTURE`, `AGENTS`, `CONSTRAINTS`,
  `RUNBOOK`, `TASKS`).

## Usage
- Prefer `uv run python scripts/validate_handles.py`.
- Default path target is `layer-gateway/registry/handles.jsonl`.
- Docs contract audit:
  - `uv run python scripts/docs_contract_audit.py`
  - `uv run python scripts/docs_contract_audit.py --json`
  - `uv run python scripts/docs_contract_audit.py --strict --json`

## Canonical references
- Registry contract context: `docs/INTEGRATIONS.md`
- Truth hierarchy: `docs/_core/SOURCES_OF_TRUTH.md`
