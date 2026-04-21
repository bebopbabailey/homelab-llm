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
- The primary worktree is baseline-only. Do not run `Build` or `Verify` there;
  start a linked worktree first with `uv run python scripts/start_effort.py ...`
  or an equivalent linked-worktree flow.
- Finish linked implementation lanes from the primary worktree with
  `uv run python scripts/closeout_effort.py --worktree <path> ...`.
- Abandon failed linked lanes from the primary worktree with
  `uv run python scripts/abandon_effort.py --worktree <path> ...`; if journal
  deltas exist, salvage them with `--salvage-journal` before pruning.
- `Build`/`Verify` work must pass local worktree-effort preflight before repo
  writes: `uv run python scripts/worktree_effort.py preflight --stage <stage>`.
- Prefer `uv run python scripts/start_effort.py --service <service-id> ...`
  when the lane maps to a canonical service in `platform/registry/services.jsonl`.
- If a dirty worktree is holding context only while another worktree builds or
  verifies, park it locally first with `uv run python scripts/worktree_effort.py park`.
- `uv run python scripts/worktree_effort.py close --json` is metadata-only; it
  does not commit, merge, or clean up the linked lane.
- Failed experiment branches may be discarded, but `docs/journal/` records must
  first be landed on `master`; never prune a branch/worktree with unsalvaged
  journal deltas.
- Local effort metadata must stay outside repo-tracked files; `NOW.md` is
  project-level status only, not a concurrent-effort registry.
- Broad parallel docs/layer lanes are not allowed. If a docs pass would claim
  `docs`, `layer-gateway`, `layer-inference`, `layer-interface`, `layer-tools`,
  `layer-data`, `services`, or `experiments` while another implementation lane
  is active, narrow the scope first.
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
If you touch anything inside a `layer-*` taxonomy surface, read first:
- `layer-*/README.md`

`layer-*` is taxonomy/navigation only. It is not a service boundary or the
authoritative architecture surface.

## Per-service consultation
If you touch a service (code, config, or docs), read first:
- the canonical service root from `platform/registry/services.jsonl`
- `<service-root>/AGENTS.md`
- `<service-root>/CONSTRAINTS.md`
- `<service-root>/RUNBOOK.md`
- `<service-root>/SERVICE_SPEC.md`

If touched files are below the service root, read every `AGENTS.md` on the path
from the service root to the touched directory, with the deepest applicable
file treated as the most specific guidance.

If any are missing, state that and proceed with the least risky interpretation.

## Scope control (monorepo)
- Prefer working within a single service boundary per task.
- Only change shared docs/registries when required by the change.
- If a change triggers doc obligations, follow `docs/_core/CHANGE_RULES.md`.
- Treat `platform/registry/services.jsonl` as the canonical taxonomy surface.
- Treat `layer-*` as thin navigation/index surfaces only.
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
