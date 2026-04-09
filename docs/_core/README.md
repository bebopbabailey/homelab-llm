# Documentation Center (_core)

## Purpose
`docs/_core` is the single navigation hub for this repo's documentation. It
does not replace existing docs; it defines how to read them.

Start at root `AGENTS.md`, then come here.

## Read Order (agents)
1. `AGENTS.md`
2. `docs/_core/README.md`
3. `docs/_core/SOURCES_OF_TRUTH.md`
4. `docs/_core/CONSISTENCY_DOD.md`
5. `DOCS_CONTRACT.md`
6. `docs/_core/CONCURRENT_EFFORTS.md`
7. `docs/PLATFORM_DOSSIER.md`
8. `docs/foundation/topology.md`
9. `docs/INTEGRATIONS.md`
10. `docs/OPENCODE.md`
11. `docs/foundation/testing.md`
12. `docs/_core/OPERATING_MODEL.md`
13. `docs/_core/CHANGE_RULES.md`
14. `docs/foundation/node-toolchain.md`

## Repo-Root Descent
- Start with root `AGENTS.md`, then use this file as the doc hub.
- Treat repo root as a narrow control surface. Dated historical packets should
  live under `docs/journal/` or `docs/archive/`, not beside the root canon.
- For a touched layer, read that layer's `AGENTS.md`, `CONSTRAINTS.md`,
  `DEPENDENCIES.md`, and `RUNBOOK.md`.
- For a touched service, read that service's `AGENTS.md`, `CONSTRAINTS.md`,
  `RUNBOOK.md`, and `SERVICE_SPEC.md`.
- If working below the service root, read each deeper applicable `AGENTS.md`
  on the path to the touched directory.
- For concurrent `Build`/`Verify` work, read
  `docs/_core/CONCURRENT_EFFORTS.md` and use one worktree per effort.

## Canonical Links
- `docs/_core/CONCURRENT_EFFORTS.md`
- `docs/foundation/overview.md`
- `docs/foundation/topology.md`
- `docs/foundation/testing.md`
- `docs/foundation/node-toolchain.md`
- `docs/PLATFORM_DOSSIER.md`
- `docs/INTEGRATIONS.md`
- `docs/OPENCODE.md`
- `docs/_core/CONSISTENCY_DOD.md`
