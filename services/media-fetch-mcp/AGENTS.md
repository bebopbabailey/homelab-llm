# Agent Guidance: media-fetch-mcp

## Scope
Keep this service localhost-only on the Mini. The first slice is a read-only
MCP backend for transcript retrieval only.

## Read First
- `README.md`
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Guardrails
- Do not expose this service on LAN-facing binds.
- Do not add summarization, translation, chunking, or vector-storage behavior
  to this service in the first slice.
- Do not widen the tool surface beyond the documented transcript retrieval
  contract without an explicit follow-on plan.
