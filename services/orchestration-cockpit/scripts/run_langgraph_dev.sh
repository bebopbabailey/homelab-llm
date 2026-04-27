#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${ORCHESTRATION_COCKPIT_ENV_FILE:-$SERVICE_ROOT/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

cd "$SERVICE_ROOT"
export PYTHONPATH="${PYTHONPATH:-./src:../omlx-runtime/src}"

exec uv run --project . langgraph dev --host 127.0.0.1 --port 2024
