# ADR 0004: LAN-First Service Traffic

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 briefly leaned on tailnet as core runtime truth, then reset to LAN-first after drift and operational fragility.

## Decision

V2 treats Mini↔Studio service traffic as LAN-first. Tailnet remains operator access, contingency, or remote UX, not core runtime truth.

## Consequences

- Core traffic uses the simpler and more durable path.
- Operator access can remain remote without redefining service contracts.
- This reduces appetite for topology designs that depend on tailnet behavior for ordinary runtime operation.

## V1 evidence

- `docs/journal/2026-03-10-studio-backend-auth-removal-and-tailnet-boundary.md`
- `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`
- `docs/foundation/topology.md`

## V2 implications

V2 docs should describe tailnet as auxiliary or operator-facing unless a later explicit decision changes that posture.
