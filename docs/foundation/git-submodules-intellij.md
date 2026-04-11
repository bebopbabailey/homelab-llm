# Git Submodules in IntelliJ

This repo does not use first-party submodules for active services.

## IntelliJ workflow
1. Open the linked worktree or repo root as the project.
2. Make changes in the normal monorepo paths.
3. Commit the lane branch in the linked worktree.
4. Close it out from the primary worktree with `scripts/closeout_effort.py`.

## Common mistakes
- Treating a service directory as if it were its own repo.
- Committing from the primary worktree instead of the linked implementation lane.
- Reviving old submodule instructions from historical docs.

## Quick checks
```bash
git status --short
uv run python scripts/worktree_effort.py status --json
```
