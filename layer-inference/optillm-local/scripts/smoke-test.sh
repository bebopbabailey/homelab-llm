#!/usr/bin/env bash
set -euo pipefail

OPTILLM_API_KEY="${OPTILLM_API_KEY:-}"
if [[ -z "$OPTILLM_API_KEY" ]]; then
  echo "OPTILLM_API_KEY not set" >&2
  exit 1
fi

curl -fsS http://127.0.0.1:4040/v1/models \
  -H "Authorization: Bearer ${OPTILLM_API_KEY}" | jq .
