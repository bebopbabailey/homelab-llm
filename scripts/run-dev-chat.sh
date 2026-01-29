#!/usr/bin/env bash
set -euo pipefail

# Run LiteLLM proxy with the current router config.
# Usage: scripts/run-dev-chat.sh

if [[ -f "config/env.local" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "config/env.local"
  set +a
else
  echo "Missing config/env.local. Copy config/env.example and set values."
  exit 1
fi

if [[ -z "${PORT:-}" || "${PORT}" == "0" ]]; then
  PORT="4000"
fi

export LITELLM_LOG="${LITELLM_LOG:-INFO}"

echo "Starting LiteLLM proxy on port ${PORT}..."
exec uv run litellm --config config/router.yaml --host 0.0.0.0 --port "${PORT}"
