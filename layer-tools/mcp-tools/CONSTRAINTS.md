# Constraints: mcp-tools

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Tools layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep this service stdio-only; do not add network listeners.
- Maintain stable tool I/O contracts and document contract changes explicitly.
- Keep secrets out of git.

## Allowed operations
- Tool implementation and docs changes within this service boundary.
- Read-only validation of MCP tool behavior.
- Contract/documentation updates when tool inputs or outputs change.

## Forbidden operations
- Adding LAN/public services, ports, or listeners.
- Hidden protocol drift without matching service-doc updates.
- Cross-layer runtime changes outside the tools boundary.

## Sandbox permissions
- Read: `layer-tools/*`
- Write: this service docs/code only
- Execute: stdio tool diagnostics/tests only

## Validation pointers
- `test -f layer-tools/mcp-tools/SERVICE_SPEC.md`
- `test -f layer-tools/mcp-tools/RUNBOOK.md`

## Change guardrail
If tool contracts change, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and integration docs in the same change.
