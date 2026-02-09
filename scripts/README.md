# scripts

Repository utility scripts.

## Current scripts
- `validate_handles.py` — validates `layer-gateway/registry/handles.jsonl`
  for schema, naming constraints, and duplicate tuple collisions.

## Usage
- Prefer `uv run python scripts/validate_handles.py`.
- Default path target is `layer-gateway/registry/handles.jsonl`.

## Canonical references
- Registry contract context: `docs/INTEGRATIONS.md`
- Truth hierarchy: `docs/_core/SOURCES_OF_TRUTH.md`
