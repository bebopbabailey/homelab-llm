#!/usr/bin/env bash
set -Eeuo pipefail

ELASTIC_URL="${MEMORY_ELASTIC_URL:-http://127.0.0.1:9200}"
SNAPSHOT_DIR="${MEMORY_ELASTIC_SNAPSHOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/runtime/elasticsearch-snapshots}"
REPO_NAME="${MEMORY_ELASTIC_SNAPSHOT_REPO:-memory-main-repo}"

curl -fsS -X PUT "${ELASTIC_URL}/_snapshot/${REPO_NAME}" \
  -H 'Content-Type: application/json' \
  -d "{\"type\":\"fs\",\"settings\":{\"location\":\"${SNAPSHOT_DIR}\",\"compress\":true}}" | jq .
