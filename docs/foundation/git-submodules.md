# Git Submodules

This repo no longer uses first-party git submodules for active services.

## Current rule
- Active first-party services are plain tracked directories in the monorepo.
- Live services now sit under `services/`; experiments and historical
  workspaces sit under `experiments/`, with only transitional taxonomy/docs
  still living under some `layer-*` roots during the refactor.
- Historical submodule guidance is retired.
- If `git ls-files --stage | grep '^160000 '` prints first-party service paths,
  repo hygiene is broken.

## Working model
```bash
git clone <repo>
cd homelab-llm
uv run python scripts/start_effort.py --id demo --scope services/litellm-orch --json
uv run python scripts/closeout_effort.py --worktree /path/to/linked-worktree --json
```

## Common mistakes
- Treating a first-party service directory as if it were its own repo.
- Reintroducing gitlinks under first-party service paths.
- Following historical submodule instructions for active lane work.

## Historical note
Older commits used first-party submodules. Current active development does not.
