#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT_DIR/.venv"

: "${MEMORY_INGEST_MODE:=jsonl}"
if [[ "$MEMORY_INGEST_MODE" == "jsonl" ]]; then
  : "${MEMORY_INGEST_PATH:?MEMORY_INGEST_PATH is required when MEMORY_INGEST_MODE=jsonl}"
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  uv venv "$VENV"
  (cd "$ROOT_DIR" && uv sync --no-dev)
fi

cd "$ROOT_DIR"
MEMORY_INGEST_MODE="$MEMORY_INGEST_MODE" "$VENV/bin/python" -m app.ingest
