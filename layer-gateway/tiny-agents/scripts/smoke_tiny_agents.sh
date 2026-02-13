#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/christopherbailey/homelab-llm"
cd "$ROOT/layer-gateway/tiny-agents"

export MCP_REGISTRY_PATH="${MCP_REGISTRY_PATH:-$ROOT/platform/ops/templates/mcp-registry.json}"
export LITELLM_API_BASE="${LITELLM_API_BASE:-http://127.0.0.1:4000/v1}"
export TINY_AGENTS_HOST="${TINY_AGENTS_HOST:-127.0.0.1}"
export TINY_AGENTS_PORT="${TINY_AGENTS_PORT:-4030}"

echo "[1/3] CLI help"
uv run tiny-agents --help >/dev/null

echo "[2/3] List MCP tools"
uv run tiny-agents list-tools

echo "[3/3] Service import sanity"
uv run python -c "from homelab_tiny_agents.service import app; print(app.title)"

echo "TinyAgents smoke checks complete."
