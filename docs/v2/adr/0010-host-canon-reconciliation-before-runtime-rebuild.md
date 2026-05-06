# ADR 0010: Host/Canon Reconciliation Before Runtime Rebuild

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

Mini and Studio inventory now show material contradictions between authoritative repo canon and observed host reality on surfaces that matter to rebuild sequencing. Rebuilding against stale canon would repeat the V1 failure modes of split authority, shadow drift, and undocumented runtime exceptions.

## Decision

No runtime rebuild slice may treat repo canon as sufficient without reconciling host reality for the touched surface first. Planning may proceed with explicit unknowns, but runtime mutation may not proceed through unresolved blockers on the surfaces that the slice intends to change.

## Consequences

- Rebuild slices get fewer silent drift assumptions.
- More up-front reconciliation work is required before mutation.
- Planning unknowns remain visible instead of being normalized into pseudo-canon.

## V1 evidence

- `docs/journal/2026-02-11-mlx-runtime-single-contract.md`
- `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`
- `docs/journal/2026-04-02-homelab-durability-eval-loop.md`
- `docs/v2/inventory/MINI_BASELINE.md`
- `docs/v2/inventory/STUDIO_BASELINE.md`

## V2 implications

V2 inventories become explicit gating inputs to runtime rebuild slices. Contradictory items may be tracked as non-blockers only when the slice does not touch that surface. Public gateway planning may proceed before MLX reconciliation, but MLX rebuild may not.
