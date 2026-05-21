#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${OMLX_ENV_FILE:-/Users/thestudio/homelab-llm-runtime/omlx-qwen36-agent/env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

OMLX_MODEL_DIR="${OMLX_MODEL_DIR:-/Users/thestudio/models/omlx-agent}"
OMLX_BASE_PATH="${OMLX_BASE_PATH:-/Users/thestudio/.omlx-qwen36-agent}"
OMLX_HOST="${OMLX_HOST:-192.168.1.72}"
OMLX_PORT="${OMLX_PORT:-8120}"
OMLX_MAX_PROCESS_MEMORY="${OMLX_MAX_PROCESS_MEMORY:-75%}"
OMLX_MAX_CONCURRENT_REQUESTS="${OMLX_MAX_CONCURRENT_REQUESTS:-4}"
OMLX_SSD_CACHE_DIR="${OMLX_SSD_CACHE_DIR:-/Users/thestudio/.omlx-qwen36-agent/cache/shadow}"
OMLX_SSD_CACHE_MAX_SIZE="${OMLX_SSD_CACHE_MAX_SIZE:-64GB}"
OMLX_HOT_CACHE_MAX_SIZE="${OMLX_HOT_CACHE_MAX_SIZE:-8GB}"

args=(
  serve
  --model-dir "$OMLX_MODEL_DIR"
  --base-path "$OMLX_BASE_PATH"
  --host "$OMLX_HOST"
  --port "$OMLX_PORT"
  --max-process-memory "$OMLX_MAX_PROCESS_MEMORY"
  --max-concurrent-requests "$OMLX_MAX_CONCURRENT_REQUESTS"
  --paged-ssd-cache-dir "$OMLX_SSD_CACHE_DIR"
  --paged-ssd-cache-max-size "$OMLX_SSD_CACHE_MAX_SIZE"
  --hot-cache-max-size "$OMLX_HOT_CACHE_MAX_SIZE"
)

if [[ -n "${OMLX_API_KEY:-}" ]]; then
  args+=(--api-key "$OMLX_API_KEY")
fi

exec /opt/homebrew/bin/omlx "${args[@]}"
