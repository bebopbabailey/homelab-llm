# Constraints: optillm-local

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Gateway layer: `../CONSTRAINTS.md`

## Hard constraints
- This directory is a placeholder only; do not treat it as an active runtime service.
- Do not deploy, bind ports, or wire new runtime paths from this directory without an explicit approved plan.
- Keep secrets out of git.

## Allowed operations
- Documentation and contract clarification inside this service directory.
- Read-only review of placeholder assets and future design notes.

## Forbidden operations
- Enabling runtime behavior from this directory.
- Wiring this directory into LiteLLM, Open WebUI, or any active gateway path.
- Adding ports, binds, listeners, or service units from here.

## Sandbox permissions
- Read: `layer-gateway/*`
- Write: this service docs only
- Execute: none required

## Validation pointers
- `test -f experiments/legacy/optillm-local-gateway/SERVICE_SPEC.md`
- `test -f experiments/legacy/optillm-local-gateway/RUNBOOK.md`

## Change guardrail
If this directory is ever promoted from placeholder to active runtime, add an explicit activation plan and update canonical platform docs before shipping.
