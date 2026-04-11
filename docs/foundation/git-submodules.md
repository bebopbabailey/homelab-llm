# Git Submodules

This repo no longer uses first-party git submodules for active services.

## Current rule
- Active first-party services under `layer-*` are plain tracked directories in
  the monorepo.
- Historical submodule guidance is retired.
- If `git ls-files --stage | grep '^160000 '` prints first-party service paths,
  repo hygiene is broken.

## Working model
```bash
git clone <repo>
cd homelab-llm
uv run python scripts/start_effort.py --id demo --scope layer-gateway/litellm-orch --json
uv run python scripts/closeout_effort.py --worktree /path/to/linked-worktree --json
```

## Common mistakes
- Treating a first-party service directory as if it were its own repo.
- Reintroducing gitlinks under first-party service paths.
- Following historical submodule instructions for active lane work.

## Historical note
Older commits used first-party submodules. Current active development does not.
