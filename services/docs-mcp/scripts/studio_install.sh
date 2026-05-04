#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${ROOT_DIR}/runtime"
mkdir -p /Users/thestudio/data/docs-mcp/logs
"${ROOT_DIR}/scripts/ensure_docs_mcp_bearer_token.sh"
echo "docs_mcp_runtime_ready"
