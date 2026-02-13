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
- **MLX control:** All MLX backend actions MUST use `mlxctl` (load/unload/assign-team/sync).
  Never start/stop `mlx-openai-server` directly on the Studio.
- Large outputs or long copy/paste blocks must go into `SCRATCH_PAD.md` for review.
- `NOW.md` must reflect the active task; update it when the active work changes.
- `NOW.md` contains only active work + a single “NEXT UP” section. Everything else goes to `BACKLOG.md`.

## Before making changes (required)
- State the goal in 1–3 lines.
- List the exact files you intend to change.
- Select verification mode (FAST or FULL) and list the commands you will run.

## Per-service consultation
If you touch a service (code, config, or docs), read first:
- `layer-*/<service>/AGENTS.md`
- `layer-*/<service>/CONSTRAINTS.md`
- `layer-*/<service>/RUNBOOK.md`

If any are missing, state that and proceed with the least risky interpretation.

## Scope control (monorepo)
- Prefer working within a single service boundary per task.
- Only change shared docs/registries when required by the change.
- If a change triggers doc obligations, follow `docs/_core/CHANGE_RULES.md`.

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
