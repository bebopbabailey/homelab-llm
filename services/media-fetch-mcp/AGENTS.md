# Agent Guidance: media-fetch-mcp

## Scope
Keep this service localhost-only on the Mini. It is the canonical HTTP MCP
retrieval boundary for media/web fetch tools, not a model-serving surface.

## Read First
- `README.md`
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Guardrails
- Do not expose this service on LAN-facing binds.
- Do not add internal summarization or model-calling behavior.
- Transcript retrieval stays source-faithful and translation-free.
- Web tools may orchestrate search/fetch/session retrieval, but only through
  documented direct dependencies like SearXNG and `vector-db`.
- Do not widen the tool surface beyond the documented MCP contract without an
  explicit follow-on plan.
