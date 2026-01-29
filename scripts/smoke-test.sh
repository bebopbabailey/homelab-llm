#!/usr/bin/env bash
set -euo pipefail

# Basic health checks for the LiteLLM proxy.
# Requires: curl, jq

BASE_URL="${BASE_URL:-http://localhost:4000}"

echo "Checking /v1/models on ${BASE_URL}..."
curl -fsS "${BASE_URL}/v1/models" | jq -e '.data | length > 0' >/dev/null

echo "Checking /v1/chat/completions on ${BASE_URL}..."
curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "main",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 16
  }' | jq -e '.choices | length > 0' >/dev/null

echo "Smoke test passed."
