#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
UV_BIN="${UV_BIN:-/home/christopherbailey/.local/bin/uv}"
export PYTHONPATH="${PYTHONPATH:-$SERVICE_ROOT/src}"

"$UV_BIN" sync --project "$SERVICE_ROOT" --frozen

exec "$UV_BIN" run --project "$SERVICE_ROOT" --no-sync python -m uvicorn omlx_agent_gateway.app:app \
  --host "${OMLX_AGENT_GATEWAY_HOST:-127.0.0.1}" \
  --port "${OMLX_AGENT_GATEWAY_PORT:-4022}"
