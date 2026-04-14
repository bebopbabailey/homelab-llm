#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/christopherbailey/homelab-llm"
SERVICE_ROOT="$REPO_ROOT/experiments/ccproxy-api"

exec "$SERVICE_ROOT/.venv/bin/ccproxy" serve \
  --config "$SERVICE_ROOT/config/ccproxy.toml" \
  --host 127.0.0.1 \
  --port 4010 \
  --auth-token "${CCPROXY_AUTH_TOKEN}" \
  --log-level WARNING
