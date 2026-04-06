# AGENTS

This file defines predictable agent behavior for this monorepo.
Primary navigation entry: `docs/_core/README.md`.

## Sources of truth
Resolve cross-document conflicts using `docs/_core/SOURCES_OF_TRUTH.md`.

## Guardrails (hard rules)
- No secrets in git (keys, tokens, credentials, private URLs). If discovered, stop and ask.
- No new LAN exposure, port changes, or host-binding changes without an explicit plan and approval.
- No dependency or lockfile churn unless the task explicitly asks for it.
- No unrelated refactors, renames, or drive-by cleanups.
- Repo-root markdown is allowlisted. Keep only stable root control-surface files
  at repo root; dated reports, review packs, one-off specs, and bulky plans go
  to `docs/journal/`, `docs/archive/`, or `next-projects/`.
- Concurrent `Build`/`Verify` efforts must use separate worktrees. Do not run
  multiple implementation passes in one dirty worktree.
- `Build`/`Verify` work must pass local worktree-effort preflight before repo
  writes: `uv run python scripts/worktree_effort.py preflight --stage <stage>`.
- If a dirty worktree is holding context only while another worktree builds or
  verifies, park it locally first with `uv run python scripts/worktree_effort.py park`.
- Local effort metadata must stay outside repo-tracked files; `NOW.md` is
  project-level status only, not a concurrent-effort registry.
- **MLX control:** Ports `8100-8119` are `mlxctl`-managed and MUST use `mlxctl`
  (load/unload/assign-team/sync). Ports `8120-8139` are experimental and do not
  require `mlxctl`.
  Mutating `mlxctl` commands require local/Studio CLI parity:
  `mlxctl studio-cli-sha` then `mlxctl sync-studio-cli` when mismatched.
  Never start/stop `mlx-openai-server` directly on the Studio.
- **Studio launchd governance:** Owned Studio labels (`com.bebop.*`, `com.deploy.*`)
  must be allowlisted and policy-audited via the Studio scheduling contract.
  Unmanaged owned labels are policy violations.
- Large outputs or long copy/paste blocks must go into `SCRATCH_PAD.md` for review.
- `NOW.md` must reflect the active task; update it when the active work changes.
- `NOW.md` contains only active work + a single “NEXT UP” section. Everything else goes to `BACKLOG.md`.

## Before making changes (required)
- State the goal in 1–3 lines.
- List the exact files you intend to change.
- Select verification mode (FAST or FULL) and list the commands you will run.

## Per-layer consultation
If you touch anything inside a layer, read first:
- `layer-*/AGENTS.md` (if present)
- `layer-*/CONSTRAINTS.md`
- `layer-*/DEPENDENCIES.md`
- `layer-*/RUNBOOK.md`

## Per-service consultation
If you touch a service (code, config, or docs), read first:
- `layer-*/<service>/AGENTS.md`
- `layer-*/<service>/CONSTRAINTS.md`
- `layer-*/<service>/RUNBOOK.md`
- `layer-*/<service>/SERVICE_SPEC.md`

If touched files are below the service root, read every `AGENTS.md` on the path
from the service root to the touched directory, with the deepest applicable
file treated as the most specific guidance.

If any are missing, state that and proceed with the least risky interpretation.

## Scope control (monorepo)
- Prefer working within a single service boundary per task.
- Only change shared docs/registries when required by the change.
- If a change triggers doc obligations, follow `docs/_core/CHANGE_RULES.md`.
- When cleaning or adding repo-root docs, preserve the root markdown allowlist
  in `DOCS_CONTRACT.md`.
- For concurrent implementation work, prefer one worktree per effort and keep
  effort scope explicit and narrow.

## Verification modes
- FAST: per-touched-service quick checks (lint/smoke/unit where they exist).
- FULL: per-touched-service runtime checks (systemd/curl/journal/bench where applicable).
  Always state which mode you used and the results. If verification was not run, say so and mark the outcome UNVERIFIED.

## Python checks
- Prefer `uv run python` for scripts and checks.
- Never run compile/test across `.venv` (exclude it explicitly).

## Output requirements (required)
After changes, report:
- Files changed
- Commands run + results
- Any skipped checks and why
