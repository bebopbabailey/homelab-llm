# Agent Guidance: Web Fetch MCP Tool

## Scope
Keep as a local stdio tool. No systemd unit unless explicitly approved.

## Read First
- `README.md`
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Guardrails
- Keep this tool on the public-web fetch contract described in the service
  docs.
- Do not widen MIME, proxy, CA-bypass, or local-network fetch behavior without
  explicit contract updates.
