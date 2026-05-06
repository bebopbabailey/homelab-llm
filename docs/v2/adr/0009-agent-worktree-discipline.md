# ADR 0009: Agent Worktree Discipline

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 hardened agent workflow around linked worktrees, narrow scope, preflight, and scripted closeout to avoid primary-worktree drift and overlapping mutable efforts.

## Decision

Mutable agent work in V2 uses linked worktrees, narrow scope, preflight, and scripted closeout. The primary worktree remains baseline-only.

## Consequences

- Concurrent mutable efforts remain isolated.
- Closeout becomes more deterministic and auditable.
- This adds ceremony to small write tasks, but reduces cross-effort contamination.

## V1 evidence

- `AGENTS.md`
- `docs/OPENCODE.md`
- `docs/journal/2026-04-02-homelab-durability-eval-loop.md`

## V2 implications

V2 planning should treat worktree-first mutation discipline as part of the operator and agent contract, not as optional workflow advice.
