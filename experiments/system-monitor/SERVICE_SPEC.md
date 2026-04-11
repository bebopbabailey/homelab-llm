# Service Spec: system-monitor

## Purpose
Gateway-layer monitoring and repair coordination. Consumes health data from
LiteLLM and backend services, and emits status snapshots and incident records.

## Host & Runtime
- Host: Mini
- Runtime: TBD

## Endpoints (planned)
- `GET /health`
- `GET /status`
- `GET /incidents`

## Notes
This is a placeholder until a dedicated repo exists.
Direct repair execution is out of scope for the current service.
