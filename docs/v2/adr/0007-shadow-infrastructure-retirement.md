# ADR 0007: Shadow Infrastructure Retirement

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 repeatedly paid cleanup costs when canary or shadow lanes stayed alive after the decision they were meant to support.

## Decision

Shadow, canary, and rollout infrastructure are temporary. After a cutover or no-go decision, they must be explicitly retired from active docs, aliases, and policy surfaces.

## Consequences

- Active truth stays closer to live reality.
- Operators stop carrying obsolete rollout vocabulary and ports.
- This shortens the grace period for “maybe later” infrastructure.

## V1 evidence

- `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`
- `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`

## V2 implications

V2 planning should assume temporary rollout artifacts have an explicit retirement step and should not become standing infrastructure by drift.
