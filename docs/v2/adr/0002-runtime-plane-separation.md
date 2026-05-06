# ADR 0002: Runtime Plane Separation

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 evidence showed that commodity inference, specialized runtime behavior, orchestration, and sandbox execution solve different problems and degrade when collapsed into one surface.

## Decision

V2 keeps commodity inference, specialized runtime, orchestration, and execution boundary as distinct planes. The specialized-runtime plane is part of V2 architecture immediately, but no concrete specialized-runtime service is required in phase one.

## Consequences

- Public compatibility stays separate from runtime-semantics experimentation.
- Orchestration and execution boundaries remain explicit instead of implicit.
- Phase-one scope stays smaller because specialized-runtime implementation is deferred until it wins concrete evals.

## V1 evidence

- `docs/foundation/runtime-planes.md`
- `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`
- `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`

## V2 implications

V2 docs should preserve the plane boundary even if the initial runtime baseline only implements commodity inference plus operator/execution surfaces.
