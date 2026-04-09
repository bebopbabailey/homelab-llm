# Constraints: Open Terminal

## Hard constraints
- Keep both Open Terminal lanes localhost-only on the Mini.
- MCP first slice is repo-root read-only only.
- Do not add `docker.sock`, host-process access, or whole-host path access.
- Do not rely on Open Terminal MCP auth as the primary security boundary.
- Keep tool calls separate from LiteLLM model calls.
- Open WebUI may register the localhost-only MCP backend directly, but only with
  the documented read-only allowlist.
- OpenHands stays denied for `/v1/mcp/*`.

## Allowed mount scope
- `/home/christopherbailey/homelab-llm:/lab/homelab-llm:ro`
- named home volume for `/home/user`

## Forbidden in this slice
- write tools
- process-control tools
- notebook enablement
- direct TinyAgents registry exposure
