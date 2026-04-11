#!/usr/bin/env bash
set -euo pipefail

# Basic health checks for the LiteLLM proxy.
# Requires: curl, jq

BASE_URL="${BASE_URL:-http://localhost:4000}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_LOCAL="${LITELLM_ENV_LOCAL:-$REPO_ROOT/layer-gateway/litellm-orch/config/env.local}"
LITELLM_API_KEY="${LITELLM_API_KEY:-}"

if [[ -z "${LITELLM_API_KEY}" && -f "$ENV_LOCAL" ]]; then
  LITELLM_API_KEY="$(grep -E '^LITELLM_MASTER_KEY=' "$ENV_LOCAL" | tail -n1 | cut -d= -f2-)"
fi

if [[ -z "${LITELLM_API_KEY}" ]]; then
  echo "missing LITELLM_API_KEY (set env or update ${ENV_LOCAL})" >&2
  exit 1
fi

echo "Checking /v1/models on ${BASE_URL}..."
curl -fsS -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  "${BASE_URL}/v1/models" | jq -e '.data | length > 0' >/dev/null

echo "Checking /v1/chat/completions on ${BASE_URL}..."
curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "main",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 16
  }' | jq -e '.choices | length > 0' >/dev/null

echo "Smoke test passed."
