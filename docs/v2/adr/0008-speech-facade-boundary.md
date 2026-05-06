# ADR 0008: Speech Facade Boundary

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 distinguished between the live speech contract and backend experiments such as XTTS environment recovery, and that separation kept the external speech path stable.

## Decision

V2 preserves one speech facade boundary. Backend ASR and TTS experiments stay behind it and do not become direct client-facing contracts until explicitly promoted.

## Consequences

- Clients consume one stable speech surface.
- Backend experimentation can proceed without contract churn.
- This limits direct exposure of backend-specific speech features until they clear serving gates.

## V1 evidence

- `docs/journal/2026-03-12-voice-gateway-xtts-runtime-proof-recovery.md`
- `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md`
- `docs/foundation/topology.md`

## V2 implications

V2 speech planning should preserve the facade principle even if the backend stack changes under it.
