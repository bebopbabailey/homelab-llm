#!/usr/bin/env bash
set -euo pipefail

if [[ -f "config/env.local" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "config/env.local"
  set +a
fi

export LITELLM_LOG="${LITELLM_LOG:-INFO}"
export PORT="${PORT:-4000}"
export CHATGPT5_ADAPTER_HOST="${CHATGPT5_ADAPTER_HOST:-127.0.0.1}"
export CHATGPT5_ADAPTER_PORT="${CHATGPT5_ADAPTER_PORT:-4011}"
export CCPROXY_ADAPTER_API_BASE="${CCPROXY_ADAPTER_API_BASE:-http://${CHATGPT5_ADAPTER_HOST}:${CHATGPT5_ADAPTER_PORT}/v1}"
venv_bin="${PWD}/.venv/bin"

"${venv_bin}/python" -m uvicorn chatgpt5_adapter:app \
  --host "${CHATGPT5_ADAPTER_HOST}" \
  --port "${CHATGPT5_ADAPTER_PORT}" &
adapter_pid=$!

cleanup() {
  kill "${adapter_pid}" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

exec "${venv_bin}/litellm" --config config/router.yaml --host 0.0.0.0 --port "${PORT}"
