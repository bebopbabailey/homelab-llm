#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT_DIR/.venv"

: "${MEMORY_DB_HOST:=127.0.0.1}"
: "${MEMORY_DB_PORT:=55432}"
: "${MEMORY_DB_USER:=memory_app}"
: "${MEMORY_DB_PASSWORD:=memory_app}"
: "${MEMORY_DB_NAME:=memory_main}"

if [[ ! -x "$VENV/bin/python" ]]; then
  uv venv "$VENV"
  (cd "$ROOT_DIR" && uv sync --no-dev)
fi

if [[ "${MEMORY_BACKEND:-elastic}" == "elastic" ]]; then
  "$ROOT_DIR/scripts/install_elasticsearch.sh"
  if [[ "${MEMORY_KIBANA_ENABLE:-true}" == "true" ]]; then
    "$ROOT_DIR/scripts/install_kibana.sh"
  fi
  "$ROOT_DIR/scripts/ensure_memory_api_write_token.sh"
fi

cd "$ROOT_DIR"
if [[ "${MEMORY_BACKEND:-elastic}" == "legacy" ]]; then
ROOT_DIR="$ROOT_DIR" "$VENV/bin/python" - <<'PY'
import os
from pathlib import Path

from app.db import connect, ensure_schema, load_db_config

root = Path(os.environ["ROOT_DIR"])
sql_dir = root / "sql"
with connect(load_db_config()) as conn:
    ensure_schema(conn, sql_dir)
print("schema_initialized")
PY
fi
