# Constraints: Open Terminal

## Hard constraints
- Keep both Open Terminal lanes localhost-only on the Mini.
- MCP first slice is repo-root read-only only.
- Do not add `docker.sock`, host-process access, or whole-host path access.
- Do not rely on Open Terminal MCP auth as the primary security boundary.
- LiteLLM remains the canonical shared client contract for MCP access.
- OpenHands stays denied for `/v1/mcp/*`.

## Allowed mount scope
- `/home/christopherbailey/homelab-llm:/lab/homelab-llm:ro`
- named home volume for `/home/user`

## Forbidden in this slice
- write tools
- process-control tools
- notebook enablement
- direct TinyAgents registry exposure
