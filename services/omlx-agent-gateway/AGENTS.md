# AGENTS - omlx-agent-gateway

## Read First
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Runtime Reality
- Mini-local sidecar only: `127.0.0.1:4022`.
- Upstream is Studio oMLX on `192.168.1.72:8120`.
- This service is not LiteLLM and must not grow LiteLLM-style routing,
  fallback, guardrail, or MCP behavior in this slice.

