# 2026-04-02 — Root allowlist and root artifact cleanup

## Why this exists
Repo root had accumulated dated reports, review packs, specs, and plans that
competed with the real root control surface.

## What changed
- Codified a repo-root markdown allowlist in `AGENTS.md`, `DOCS_CONTRACT.md`,
  `README.md`, and `docs/_core/README.md`.
- Moved historical root packets into `docs/archive/`.
- Moved the active OpenHands harness plan into `next-projects/`.
- Kept root reserved for stable monorepo orientation and live control files.

## Root allowlist
- `AGENTS.md`
- `README.md`
- `DOCS_CONTRACT.md`
- `CONSTRAINTS.md`
- `SYSTEM_OVERVIEW.md`
- `TOPOLOGY.md`
- `DIAGNOSTICS.md`
- `INCIDENT_FLOW.md`
- `SANDBOX_PERMISSIONS.md`
- `NOW.md`
- `BACKLOG.md`
- `SCRATCH_PAD.md`

## Archive summaries added
- `docs/archive/2026-03-gpt-oss-vllm-metal-experimental-campaign.md`
- `docs/archive/2026-03-opencode-planner-and-caller-experiments.md`
- `docs/archive/2026-03-main-lane-cutover-and-shadow-history.md`
- `docs/archive/2026-02-optillm-mlx-backend-experimental-foundation.md`
- `docs/archive/2026-02-studio-scheduling-policy-plan.md`
- `docs/archive/2026-01-deploy-user-plan.md`
- `docs/archive/2026-03-studio-team-lane-swap-instructions.md`

## Outcome
- Repo root is now a narrower, higher-trust search surface for coding agents.
- Historical evidence remains available without masquerading as root canon.
