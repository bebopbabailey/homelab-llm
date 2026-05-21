#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
UV_BIN="${UV_BIN:-/home/christopherbailey/.local/bin/uv}"
export PYTHONPATH="$SERVICE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

exec "$UV_BIN" run --no-project --with fastapi --with uvicorn --with pydantic python -m uvicorn omlx_agent_gateway.app:app \
  --host "${OMLX_AGENT_GATEWAY_HOST:-127.0.0.1}" \
  --port "${OMLX_AGENT_GATEWAY_PORT:-4022}"
