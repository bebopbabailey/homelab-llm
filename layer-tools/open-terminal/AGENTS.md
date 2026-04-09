# Agent Guidance: Open Terminal

## Scope
Keep this service localhost-only on the Mini. The first slice is read-only MCP
for repo inspection only.

## Required guardrails
- Do not expose this service on LAN-facing binds.
- Do not widen beyond the documented read-only tool subset without an explicit
  follow-on plan.
- Do not add `docker.sock`, whole-host binds, or write mounts.

## Runtime
- MCP service: `mcp --transport streamable-http`
- Bind: `127.0.0.1:8011` on the Mini
- Current live client path: direct localhost MCP backend
- Shared LiteLLM MCP alias: future work only
- Optional separate human UX path: native Open Terminal API on `127.0.0.1:8010`
