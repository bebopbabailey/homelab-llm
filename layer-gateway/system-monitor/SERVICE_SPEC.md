# Service Spec: system-monitor (placeholder)

## Purpose
Gateway-layer monitoring and repair coordination. Consumes health data from
LiteLLM and backend services, emits status snapshots and (later) repair actions.

## Host & Runtime
- Host: Mini (gateway host)
- Runtime: TBD (lightweight service)

## Endpoints (planned)
- `GET /health`
- `GET /status`
- `GET /incidents`

## Data
- Uses the System Documentation DB (SQLite-first).
- Monitoring views derived from canonical tables.

## Notes
This is a placeholder until a dedicated repo exists.
