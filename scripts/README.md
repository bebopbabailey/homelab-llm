# scripts

Repository utility scripts.

## Current scripts
- `validate_handles.py` — validates `layer-gateway/registry/handles.jsonl`
- `docs_contract_audit.py` — audits layer/service docs bundle completeness
- `repo_hygiene_audit.py` — audits root/journal/archive hygiene
- `control_plane_sync_audit.py` — audits repo-local control-plane sync
- `docs_link_audit.py` — audits internal markdown links on the supported
  documentation surface
- `worktree_effort.py` — manages local per-worktree effort metadata
- `start_effort.py` — creates a linked worktree and runs preflight

## Usage
- Docs contract audit:
  - `uv run python scripts/docs_contract_audit.py --strict --json`
- Repo hygiene audit:
  - `uv run python scripts/repo_hygiene_audit.py --json`
- Control-plane sync audit:
  - `uv run python scripts/control_plane_sync_audit.py --strict --json`
- Docs link audit:
  - `uv run python scripts/docs_link_audit.py`
  - checks root markdown, `docs/**`, layer/service bundle markdown,
    `platform/ops/README.md`, and `scripts/README.md`
- Worktree effort preflight:
  - `uv run python scripts/start_effort.py --id <id> --scope <repo-path> --json`
  - `uv run python scripts/worktree_effort.py park --notes "holding context" --json`
  - `uv run python scripts/worktree_effort.py preflight --stage build --json`
  - `uv run python scripts/worktree_effort.py close --json`

## Canonical references
- `docs/INTEGRATIONS.md`
- `docs/_core/SOURCES_OF_TRUTH.md`
