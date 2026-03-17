# Constraints: orin-llm-server

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Inference layer: `../CONSTRAINTS.md`

## Hard constraints
- This directory is documentation-only unless an explicit approved runtime plan says otherwise.
- Do not add ports, listeners, service units, or deployment wiring from this directory by default.
- Keep secrets out of git.

## Allowed operations
- Documentation and contract updates for the placeholder service.
- Read-only planning notes that clearly mark the service as inactive.

## Forbidden operations
- Pretending this service is active when it is not.
- Adding runtime configuration, systemd/launchd units, or deployment steps from here without approval.
- Cross-layer wiring into active inference/gateway paths.

## Sandbox permissions
- Read: `layer-inference/*`
- Write: this service docs only
- Execute: none required

## Validation pointers
- `test -f layer-inference/orin-llm-server/SERVICE_SPEC.md`
- `test -f layer-inference/orin-llm-server/RUNBOOK.md`

## Change guardrail
If this service is ever activated, update canonical topology/runtime docs and add explicit operational validation before claiming it is live.
