# ADR 0001: One Public Gateway

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 repeatedly converged on one boring public gateway after experiments, shadows, and backend-specific lanes created drift and extra operator burden.

## Decision

V2 keeps one boring public gateway for commodity inference. Experimental, private, or specialized backends do not join the public contract without explicit promotion.

## Consequences

- Public clients get one stable contract.
- Backend experiments can continue without redefining the public surface.
- This restricts direct promotion of attractive experimental systems until they clear explicit gates.

## V1 evidence

- `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`
- `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`
- `README.md`

## V2 implications

V2 planning should describe one client-facing gateway and treat any additional runtime path as private, candidate, or historical until promoted.
