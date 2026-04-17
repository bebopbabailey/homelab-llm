#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

exec uv run \
  --with fastapi \
  --with uvicorn \
  --with qwen-agent==0.0.34 \
  --with numpy \
  --with soundfile \
  --with python-dateutil \
  --with pebble \
  --with multiprocess \
  --with timeout_decorator \
  --with scipy \
  --with sympy \
  python -m uvicorn qwen_agent_proxy.service:app \
    --app-dir "$SERVICE_ROOT/src" \
    --host "${QWEN_AGENT_PROXY_HOST:-127.0.0.1}" \
    --port "${QWEN_AGENT_PROXY_PORT:-4021}"
