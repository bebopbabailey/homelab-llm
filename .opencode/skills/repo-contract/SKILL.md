---
name: repo-contract
description: Load the repo contract, required docs, and verification obligations for this monorepo
compatibility: opencode
---

## What I do

- Read root `AGENTS.md`.
- Use `docs/_core/README.md` as the documentation hub.
- Use `docs/_core/SOURCES_OF_TRUTH.md` to resolve cross-document conflicts.
- Use `docs/_core/CHANGE_RULES.md` when work changes documented runtime claims or
  validation assumptions.

## Descent workflow

- If touching a layer, read that layer's `AGENTS.md`, `CONSTRAINTS.md`,
  `DEPENDENCIES.md`, and `RUNBOOK.md`.
- If touching a service, read that service's `AGENTS.md`, `CONSTRAINTS.md`,
  `RUNBOOK.md`, and `SERVICE_SPEC.md`.
- If working below the service root, read each deeper applicable `AGENTS.md` on
  the path to the touched directory.

## Execution obligations

- Before changes, state the goal, exact files, and verification mode.
- After work, report files changed, commands run with results, and any skipped
  checks.
