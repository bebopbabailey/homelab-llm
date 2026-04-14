# Concurrent Efforts

Use this contract when multiple implementation agents or chats may be active at
the same time.

## Core rule
- One implementation effort per worktree.
- The primary worktree is baseline-only.
- `Build` and `Verify` work must not share a dirty worktree.
- `NOW.md is project-level status`, not the effort registry.
- If a dirty worktree is holding context only while another worktree builds or verifies, park it locally first.
- Start new implementation work from the primary worktree with `uv run python scripts/start_effort.py ...`, then mutate only in the linked worktree it creates.
- Prefer `uv run python scripts/start_effort.py --service <service-id> ...`
  when the lane maps to a canonical service registry entry.
- Land a finished linked lane from the primary worktree with
  `uv run python scripts/closeout_effort.py --worktree <path> ...`.
- Broad parallel docs/layer lanes are invalid while another implementation
  effort is active; the same rule applies to broad `services` and
  `experiments` scopes. Narrow them to explicit non-overlapping files or
  service roots first.
- `layer-*` survives only as README.md taxonomy/navigation surfaces and is not
  a live service-root boundary.

## Local-only effort metadata
Concurrent effort state is local to each worktree and must not be tracked in
git.

Storage:
- `<git-dir>/codex-effort.json`

Examples:
- main worktree: `.git/codex-effort.json`
- linked worktree: `.git/worktrees/<name>/codex-effort.json`

Required fields:
- `effort_id`
- `stage`
- `scope_paths`
- `status`
- `created_at`
- `updated_at`

Local-only parked context:
- `stage=parked` means the worktree is intentionally holding dirty context and must not mutate until it is re-registered for `build` or `verify`.
- Parked worktrees do not count as implementation efforts and do not block other worktrees by themselves.

## Effort lifecycle
1. If the worktree is dirty but context-only, park it first:

```bash
uv run python scripts/worktree_effort.py park --notes "holding dirty context" --json
```

2. Register the local effort before `Build` or `Verify` work:

Normal path:

```bash
uv run python scripts/start_effort.py --id <effort-id> --scope <repo-relative-path>
uv run python scripts/start_effort.py --id <effort-id> --service <service-id>
```

Manual fallback:

```bash
uv run python scripts/worktree_effort.py register \
  --effort-id <effort-id> \
  --stage build \
  --scope <repo-relative-path> \
  --owner codex
```

3. Run local preflight before writes:

```bash
uv run python scripts/worktree_effort.py preflight --stage build --json
uv run python scripts/worktree_effort.py preflight --stage verify --json
```

4. Close the effort when the worktree is no longer the active implementation
   surface:

```bash
uv run python scripts/worktree_effort.py close --json
```

`close` deletes the local metadata file and returns the worktree to a true null state.

5. Close out a finished linked lane from the primary worktree:

```bash
uv run python scripts/closeout_effort.py --worktree <linked-worktree-path> --json
```

`closeout_effort.py` is the lane-landing command. It may commit scoped work,
run repo audits, fast-forward merge to `master`, close metadata, remove the
linked worktree, and delete the local branch. It does not auto-rebase or edit
`NOW.md`.

## Scope rules
- `scope_paths` are repo-relative path prefixes, not globs.
- Service registry entries provide canonical service roots; `--service` expands
  to the registry path before overlap checks run.
- Parent/child overlaps count as conflicts.
- Sibling paths do not overlap by default.
- Reject absolute paths and any path containing `..`.

Examples:
- `docs` overlaps `docs/INTEGRATIONS.md`
- `scripts/worktree_effort.py` overlaps only itself
- `services/openhands` overlaps any file below that service root

## Preflight meaning
`Build` or `Verify` preflight fails when:
- the current worktree is the primary worktree
- there is no active local effort
- the current worktree is parked
- the local effort has no declared scope
- the current worktree has dirty paths outside the declared scope
- another active worktree has overlapping scope
- another active worktree reuses the same `effort_id`
- another dirty worktree has no active effort metadata
- `master` hosts more than one active implementation effort
- a broad parallel docs/layer lane is being bootstrapped while another
  implementation effort is active

Primary baseline health also degrades when:
- the primary worktree is not on `master`
- the primary worktree is dirty
- the primary worktree is parked
- the primary worktree has an active implementation effort

`Discover` and `Design` do not hard-fail by default, but should warn when the
local worktree is not registered or other dirty worktrees exist without effort
metadata.

## Choosing the right coordination surface
- Use `NOW.md` for project-level active work and next-up status.
- Use local worktree effort metadata for concurrent implementation ownership.
- Do not add a repo-tracked active-effort registry.
- Treat the primary worktree as baseline-only, not as a fallback implementation lane.
- Treat `close` as metadata-only. Use `closeout_effort.py` when you mean “land
  the lane and restore the boring baseline.”

## Two-agent example
- Agent A:
  - worktree: `~/wt-main-context`
  - command: `uv run python scripts/worktree_effort.py park --notes "holding dirty context" --json`
  - state: `parked`
- Agent B:
  - worktree: `~/wt-openhands`
  - effort: `openhands-secret-persistence`
  - scope: `services/openhands`, `platform/ops/systemd/openhands.service`

These can run in parallel because the context worktree is explicitly parked and
the implementation worktree has its own scope and preflight.
