# TinyAgents (MVP orchestration)

## Overview
TinyAgents here is a local homelab orchestrator package that provides:

1) a CLI runner (`tiny-agents`), and
2) a localhost-only HTTP service (`tiny-agents-service`).

It calls LiteLLM as the single LLM gateway and uses MCP tools via the runtime
registry. It must not call inference backends directly.

## Status and Constraints
- MCP tools are implemented locally; TinyAgents is the MVP orchestrator.
- No new LAN-exposed services without approval.
- Use `uv` for Python dependency management.

## Install (uv-only)
Install dependencies from local `pyproject.toml`:

```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/tiny-agents
uv sync
```

## Configuration (MVP)
- LiteLLM base URL: `LITELLM_API_BASE=http://127.0.0.1:4000/v1`
- LiteLLM auth env key name: `LITELLM_API_KEY_ENV=LITELLM_API_KEY` (default)
- MCP registry (runtime): `MCP_REGISTRY_PATH=/etc/homelab-llm/mcp-registry.json`
- Service bind: `TINY_AGENTS_HOST=127.0.0.1`
- Service port: `TINY_AGENTS_PORT=4030`
- Template env: `platform/ops/templates/tiny-agents.env`.

## CLI usage

```bash
# List tools from registry
uv run tiny-agents list-tools

# One-shot run
uv run tiny-agents run --model main --message "openvino llm"

# Scaffold a new MCP tool skeleton (not auto-enabled)
uv run tiny-agents scaffold-tool demo-tool
```

## Service usage (localhost only)

```bash
# Start service
uv run tiny-agents-service

# Health
curl -fsS http://127.0.0.1:4030/health | cat

# Run request
curl -fsS http://127.0.0.1:4030/run \
  -H "Content-Type: application/json" \
  -d '{
    "model": "main",
    "messages": [{"role": "user", "content": "openvino llm"}],
    "max_tool_calls": 1
  }' | cat
```

## MCP smoke (local tools)
Use the web-fetch MCP server to validate `search.web` and `web.fetch`:

```bash
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 /home/christopherbailey/homelab-llm/layer-gateway/tiny-agents/scripts/mcp_smoke.py --tool search.web
```

## TinyAgents smoke

```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/tiny-agents
bash scripts/smoke_tiny_agents.sh
```

## References
- MCP overview: `https://modelcontextprotocol.io/`
- Plain-English explainer: `docs/WHAT_TINY_AGENTS_DOES.md`
- Request/response examples: `docs/REQUEST_FLOW_EXAMPLE.md`
