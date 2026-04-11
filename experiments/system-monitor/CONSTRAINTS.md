# Constraints: system-monitor

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Gateway layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep this service read-only with respect to other services.
- Monitoring may observe health, logs, and status, but must not perform repairs or config mutation by itself.
- Keep secrets out of git.

## Allowed operations
- Documentation updates within this service.
- Read-only health/status/logging logic scoped to monitoring.
- Validation of monitoring contracts and expected inputs.

## Forbidden operations
- Restarting or reconfiguring other services from this service boundary.
- Hidden control-plane behavior or automatic repair loops.
- Cross-layer config changes without explicit approval.

## Sandbox permissions
- Read: `layer-gateway/*`
- Write: this service docs/config only
- Execute: read-only health/status commands only

## Validation pointers
- `test -f experiments/system-monitor/SERVICE_SPEC.md`
- `test -f experiments/system-monitor/RUNBOOK.md`

## Change guardrail
If this service ever gains write/repair behavior, document the escalation and approval model first and update canonical docs before implementation.
