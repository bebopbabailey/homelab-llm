# Tools Layer Constraints

## Hard constraints
- Keep tools local-only unless explicitly approved.
- Do not expose new LAN endpoints by default.
- Do not add MCP tools without registry + documentation updates.

## Sandbox permissions
- Read: `layer-tools/*`
- Write: tool configs + docs only
- Execute: restart tool services only (SearXNG); MCP tools remain stdio
- Forbidden: new LAN exposure, adding tools without registry updates

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.
