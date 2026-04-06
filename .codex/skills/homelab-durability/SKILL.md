---
name: homelab-durability
description: Stage-aware durability workflow for this repo; lighter during discovery/design, strict for writes and risky ops. Use for homelab-durability or homelab_durability.
---

# Homelab Durability

## Purpose
- Keep discovery and planning light, but become stricter as work approaches mutation, runtime impact, or host risk.
- Preserve boring, durable operating behavior: read-only first, narrow diffs, strong source-of-truth discipline, and explicit rollback where runtime safety depends on it.

## When to use
- Use this skill for repo-local work that needs strong host awareness, scoped edits, runtime caution, or validation-heavy execution.
- Do not use it as a universal header generator for every read-only turn.

## Required startup declaration
- Before proposing commands or file edits, state: `Host`, `Scope`, `Files`, `Verification mode`.
- For repo-local non-runtime work, `Host` may be `local workspace only`.
- For host-affecting ops, `Host` must be explicit: `Mini`, `Studio`, or `Orin`.
- For command-only read-only work, `Files` may be `none` or `read-only within <scope>`.
- For any write, `Files` must be an explicit list.

## File discipline
- No file writes without an explicit file list.
- Read-only discovery may inspect broadly within the declared scope.
- If likely touched files are not yet known, produce a candidate file list and stop.
- Keep diffs narrow and scoped to the active task.

## Repo etiquette
- `Discover` may proceed in a dirty tree, but must remain read-only.
- `Design` may proceed in a dirty tree, but should call out when existing changes reduce confidence.
- `Build` or `Verify` should not proceed with writes blindly in a dirty tree.
- If unrelated changes are present, prefer one of: commit the current work, stash it, or move the new effort to a separate branch or worktree.
- If multiple chats or efforts are active, prefer a separate worktree per effort.
- For concurrent implementation work, use local worktree-effort metadata rather
  than `NOW.md` as the coordinator.
- If another worktree is dirty but context-only, park it locally before
  mutating elsewhere.
- Before proposing edits, surface repo state briefly when it matters to safety or diff clarity.
- Do not mix opportunistic cleanup with the requested change unless explicitly approved.

## Modes / stages
- `Discover`: read-only, low-friction, broad inspection within scope, no formal startup header unless commands are being proposed.
- `Design`: choose an approach, state assumptions, and surface candidate files or confidence risks without forcing rollback language.
- `Build`: strict on writes and mutations. Require the startup declaration before commands or edits. Keep the hard blocks below in force.
- `Build`: if another worktree is only holding dirty context, use `uv run python scripts/worktree_effort.py park --notes "<reason>" --json` there instead of relying on ad hoc `design` registration.
- `Build`: before proposing file edits or mutation commands, run or propose `uv run python scripts/worktree_effort.py preflight --stage build --json`.
- `Verify`: strict on validation reporting. State verification mode and results. Require rollback only when the action class needs it.
- `Verify`: before proposing verification-stage mutations, run or propose `uv run python scripts/worktree_effort.py preflight --stage verify --json`.
- Operating rhythm: `Inventory -> Constraints -> Minimal contract -> Wire -> Validate -> Codify -> Prune`.

## Sources of truth
- Always consult first:
  - `AGENTS.md`
  - `docs/_core/SOURCES_OF_TRUTH.md`
  - `docs/foundation/operating-rhythm.md`
- Consult when changing docs, process, or platform description:
  - `docs/_core/CHANGE_RULES.md`
  - `docs/_core/root_hygiene_manifest.json` when changing root/journal/archive placement rules
  - `docs/_core/OPERATING_MODEL.md`
  - `docs/PLATFORM_DOSSIER.md`
  - `docs/foundation/topology.md`
- Consult when touching gateway or runtime behavior:
  - `docs/_core/CHANGE_RULES.md`
  - `layer-gateway/CONSTRAINTS.md`
  - relevant service `SERVICE_SPEC.md`, `RUNBOOK.md`, and `CONSTRAINTS.md`

## Rollback discipline
- Rollback is required for service restarts, running-system config changes, destructive operations, and host-level mutations.
- Rollback is not required for pure planning, read-only analysis, or docs-only work.
- When rollback is required, include it before execution, not after.

## Output expectations
- `Discover` and `Design` should stay compact and high-signal. Do not force ceremonial headers when no commands or edits are being proposed.
- `Build` and `Verify` should include the startup declaration before commands or file edits.
- Include `Commands` only when commands are being proposed.
- Include `Validation` when checks are being run or proposed.
- Include `Rollback` only when the work class requires it.
- When repo-entry hygiene is part of the task, prefer the machine-checked
  contract over prose memory: root allowlist and archive shape should follow the
  validator-backed manifest, not ad hoc judgment.
- For concurrent implementation work, do not treat `NOW.md` as the effort
  registry; use local worktree-effort metadata and preflight instead.
- `close` should return a worktree to a null state by removing the local
  metadata file.

## Invocation aliases
- Invoke by name: `homelab-durability` or `homelab_durability`.

## Hard blocks and safety defaults
- Download approval threshold: 500MB.
- Disk check required before any model download/cache action or any explicitly large (>5GB) action: YES.
- Host confirmation is strict for ops commands, but may be treated as sticky within the same session after explicit confirmation.
- Violations: HARD-BLOCK for MLX/disk/host/file-list rules; WARN for stylistic rules.
- No multi-file edits without an explicit file list.
- No ops commands unless the host check is explicitly satisfied in the same response.
- No restarts or service modifications unless the current work is in `Build` or `Verify` and a rollback is specified when required.
- No disk repair / fsck / apfs repair / partition changes without explicit user approval.
- MLX backends: MUST use `mlxctl` plus the registry as the source of truth. No ad-hoc edits or direct `mlx-openai-server` control unless explicitly authorized.
- Any download/cache/model pull > 500MB requires explicit user approval.
- Before any model download/cache action or any explicitly large (>5GB) action, require a disk free check command suggestion and stop until the user confirms.
- Default to read-only inspection first.
- Explicitly confirm target host and its role.
- If not confirmed, STOP and ask for confirmation.
