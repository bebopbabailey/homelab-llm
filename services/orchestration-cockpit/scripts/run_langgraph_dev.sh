#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="${ORCHESTRATION_COCKPIT_REPO_ROOT:-$(cd -- "$SERVICE_ROOT/../.." && pwd)}"
STATE_DIR="${ORCHESTRATION_COCKPIT_STATE_DIR:-$HOME/.local/state/orchestration-cockpit}"
GRAPH_RUNTIME_DIR="${ORCHESTRATION_COCKPIT_GRAPH_RUNTIME_DIR:-$STATE_DIR/langgraph-runtime}"
ARTIFACT_DIR="${ORCHESTRATION_COCKPIT_ARTIFACT_DIR:-$STATE_DIR}"
GRAPH_HOST="${ORCHESTRATION_COCKPIT_GRAPH_HOST:-127.0.0.1}"
GRAPH_PORT="${ORCHESTRATION_COCKPIT_GRAPH_PORT:-2024}"
RUNTIME_CONFIG_PATH="${ORCHESTRATION_COCKPIT_RUNTIME_CONFIG_PATH:-$GRAPH_RUNTIME_DIR/langgraph.json}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$HOME/.local/share/orchestration-cockpit/graph-venv}"
export ORCHESTRATION_COCKPIT_ARTIFACT_DIR="$ARTIFACT_DIR"
export PYTHONPATH="${PYTHONPATH:-$SERVICE_ROOT/src:$REPO_ROOT/services/omlx-runtime/src}"

mkdir -p "$GRAPH_RUNTIME_DIR" "$ARTIFACT_DIR" "$(dirname "$UV_PROJECT_ENVIRONMENT")"
uv sync --project "$SERVICE_ROOT" --frozen
uv run --project "$SERVICE_ROOT" --no-sync python \
  "$SERVICE_ROOT/scripts/render_langgraph_runtime_config.py" \
  --output "$RUNTIME_CONFIG_PATH"
cd "$GRAPH_RUNTIME_DIR"

exec uv run --project "$SERVICE_ROOT" --no-sync langgraph dev \
  --config "$RUNTIME_CONFIG_PATH" \
  --no-browser \
  --no-reload \
  --host "$GRAPH_HOST" \
  --port "$GRAPH_PORT"
