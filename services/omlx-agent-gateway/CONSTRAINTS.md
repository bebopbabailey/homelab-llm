# Constraints: omlx-agent-gateway

## Hard Constraints
- Bind only to `127.0.0.1`.
- Keep upstream model behavior as the source of truth.
- Do not add LiteLLM aliases, Open WebUI routes, OpenHands policy, or MCP proxying.
- Do not store bearer tokens or Studio API keys in tracked files.

## Allowed Operations
- Add minimal model discovery, model-info, health, and chat-completion passthrough.
- Normalize the public sidecar model id to the Studio oMLX backend model id.
- Surface upstream HTTP, parse, and transport failures cleanly.

## Validation
- `uv run --project services/omlx-agent-gateway pytest`
- `curl -fsS http://127.0.0.1:4022/health`
- `curl -fsS http://127.0.0.1:4022/v1/models`

