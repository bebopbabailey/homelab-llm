# Testing and Verification

This doc captures the recommended test steps for new changes. Run these on the
appropriate host and confirm outputs before declaring a change complete.

## Documentation integrity
Run these for doc-heavy changes before sign-off:
```bash
uv run python scripts/docs_contract_audit.py --strict --json
uv run python scripts/repo_hygiene_audit.py --json
uv run python scripts/control_plane_sync_audit.py --strict --json
uv run python scripts/docs_link_audit.py
```

Expected:
- docs bundle contracts stay complete
- root_ok and journal_index_ok remain true
- control-plane sync remains aligned
- internal markdown links on the supported doc surface resolve cleanly

## Concurrent effort checks
- `uv run python scripts/start_effort.py --id <id> --scope <repo-path> --json`
- `uv run python scripts/worktree_effort.py park --notes "holding context" --json`
- `uv run python scripts/worktree_effort.py close --json`
- The primary worktree remains baseline-only for `Build` and `Verify`.

## Runtime Lock
FAST validator:
```bash
python3 platform/ops/scripts/validate_runtime_lock.py --mode fast --json
```

FULL validator:
```bash
python3 platform/ops/scripts/validate_runtime_lock.py --mode full --host studio --json
```

Expected:
- FAST passes in local CI/repo state with no patch artifacts or git-sourced
  OptiLLM.
- FULL confirms Studio OptiLLM exact-SHA deploy plus MLX lane `auto` with the
  locked parser/runtime assumptions.
