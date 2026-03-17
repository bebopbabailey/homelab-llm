# Constraints: tiny-agents

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Gateway layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep TinyAgents as a client/orchestrator only.
- Preserve localhost-only service exposure for any service-mode execution unless an approved migration plan says otherwise.
- Do not bypass LiteLLM for model access.
- Keep MCP registry references externalized and keep secrets out of git.

## Allowed operations
- Service-local CLI/config/docs updates.
- Validation of local orchestration behavior within this service boundary.
- Read-only diagnostics for LiteLLM-facing agent flows.

## Forbidden operations
- New LAN exposure or host-binding changes without explicit approval.
- Direct backend model calls that bypass LiteLLM.
- Cross-layer runtime wiring outside this service scope.

## Sandbox permissions
- Read: `layer-gateway/*`
- Write: this service docs/config/code only
- Execute: service-local diagnostics only

## Validation pointers
- `test -f layer-gateway/tiny-agents/SERVICE_SPEC.md`
- `test -f layer-gateway/tiny-agents/RUNBOOK.md`

## Change guardrail
If TinyAgents exposure, gateway pathing, or tool contracts change, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and canonical integration docs in the same change.
