# Tools Layer Constraints

## Hard constraints
- Keep tools local-only unless explicitly approved.
- Do not expose new LAN endpoints by default.
- Do not add MCP tools without the required documentation updates.
- Registry-managed tools must update the MCP registry template/runtime file.
- LiteLLM-managed HTTP MCP backends must stay out of the registry unless a
  separate approved plan explicitly widens that client surface.

## Sandbox permissions
- Read: `layer-tools/*`
- Write: tool configs + docs only
- Execute: restart/check local tool services (`searxng`, `open-terminal-mcp`)
- Forbidden: new LAN exposure, adding registry-managed tools without registry
  updates

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.
