# MCP Tools (Planned)

## Purpose
MCP servers expose tools that agents can call. In this platform:
- **LLM calls** go through LiteLLM only.
- **Tool calls** go through MCP servers.

TinyAgents is the default MCP client that discovers and calls tools.

## Recommended Timing
Adopt MCP once these are stable:
- LiteLLM routing and model registry are reliable.
- Tool endpoints (e.g., SearXNG, repos, ops scripts) are defined.
- Basic health checks and logging are in place.

Start with one or two tools, validate the workflow, then scale.

## How LLMs Use MCP
LLMs do not talk to MCP servers directly.
An agent runtime (e.g., TinyAgents) interprets the model output, selects tools,
and calls MCP servers, then feeds results back to the LLM via the same
conversation.

## MCP Server Inventory (planned)
Maintain a simple registry of MCP servers with:
- Name and purpose
- Transport (stdio vs HTTP/SSE)
- Endpoint or command
- Required environment variables

## Tool Contract Guidelines
- Document inputs, outputs, and error cases.
- Version tool schemas to avoid breaking changes.
- Keep tools small and composable.

