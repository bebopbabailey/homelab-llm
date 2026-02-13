# Runbook: TinyAgents

TinyAgents supports CLI mode and localhost-only service mode.

## Prerequisites
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/tiny-agents
uv sync
```

Ensure env values are present (see `platform/ops/templates/tiny-agents.env`):
- `LITELLM_API_BASE`
- `LITELLM_API_KEY` (referenced by `LITELLM_API_KEY_ENV`)
- `MCP_REGISTRY_PATH`
- `TINY_AGENTS_HOST=127.0.0.1`
- `TINY_AGENTS_PORT=4030`

## CLI mode
```bash
uv run tiny-agents list-tools
uv run tiny-agents run --model main --message "openvino llm"
```

## Service mode (localhost only)
```bash
uv run tiny-agents-service
curl -fsS http://127.0.0.1:4030/health | cat
```

## Smoke checks
```bash
bash /home/christopherbailey/homelab-llm/layer-gateway/tiny-agents/scripts/smoke_tiny_agents.sh
```

## Notes
- This service must remain bound to `127.0.0.1`.
- Do not bypass LiteLLM for model calls.
