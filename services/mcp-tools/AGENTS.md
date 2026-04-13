# Agent Guidance: mcp-tools

## Scope
Only change `services/mcp-tools/*`.

## Non-negotiables
- Do not add network listeners without an explicit plan and approval.
- Do not commit secrets.
- Keep tool IO contracts stable; update `docs/INTEGRATIONS.md` when needed.
- If touching `web-fetch/*`, also read `web-fetch/AGENTS.md`,
  `web-fetch/RUNBOOK.md`, and `web-fetch/SERVICE_SPEC.md`.
