# Constraints: web-fetch

This service inherits global + parent-service constraints:
- Global: `../../../CONSTRAINTS.md`
- Tools layer guidance: `../../../layer-tools/CONSTRAINTS.md`
- Parent service: `../CONSTRAINTS.md`

## Hard constraints
- Keep this tool stdio-only; do not add HTTP listeners or other network binds.
- Limit fetches to the documented public-web contract; no local-network,
  loopback, or host-internal fetch widening without explicit contract updates.
- Do not weaken MIME allowlisting, TLS verification, proxy isolation, or SSRF
  guardrails without matching service-doc changes.
- Keep secrets and API keys out of git.

## Allowed operations
- Tool implementation and docs changes within this child service boundary.
- Read-only smoke tests through the demo client or MCP client.
- Contract/documentation updates when tool inputs, outputs, or safety limits
  change.

## Forbidden operations
- Adding LAN/public service exposure.
- Hidden protocol drift without matching service-doc updates.
- Relaxing fetch safety defaults as an implementation shortcut.

## Sandbox permissions
- Read: `services/mcp-tools/web-fetch/*` plus parent `services/mcp-tools/*` guidance
- Write: this child service docs/code only
- Execute: stdio tool diagnostics/tests only

## Validation pointers
- `test -f services/mcp-tools/web-fetch/SERVICE_SPEC.md`
- `test -f services/mcp-tools/web-fetch/RUNBOOK.md`
- `.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text`

## Change guardrail
If fetch safety, output modes, or search/web tool contracts change, update
`SERVICE_SPEC.md`, `RUNBOOK.md`, and integration docs in the same change.
