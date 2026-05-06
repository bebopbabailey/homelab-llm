# ADR 0003: Registry-Derived Routing

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 drifted when live routing, boot config, and runtime truth were owned by different surfaces.

## Decision

V2 derives gateway routing and runtime exposure from one registry/runtime source of truth. Split boot/runtime authority is not allowed.

## Consequences

- Routing changes become auditable and reproducible.
- Generated config outranks hand-maintained duplication.
- This constrains ad hoc runtime overrides that bypass the control plane.

## V1 evidence

- `docs/journal/2026-01-18-mlx-sync-gateway.md`
- `docs/journal/2026-02-11-mlx-runtime-single-contract.md`
- `docs/INTEGRATIONS.md`

## V2 implications

V2 migration should prefer registry-derived config generation and reject any architecture that needs separate truth surfaces for boot and live routing.
