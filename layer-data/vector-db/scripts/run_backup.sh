#!/usr/bin/env bash
set -Eeuo pipefail

: "${MEMORY_DB_HOST:=127.0.0.1}"
: "${MEMORY_DB_PORT:=55432}"
: "${MEMORY_DB_USER:=memory_app}"
: "${MEMORY_DB_NAME:=memory_main}"
: "${MEMORY_DB_PASSWORD:=memory_app}"
: "${MEMORY_BACKUP_DIR:=/Users/thestudio/data/memory-main/backups}"
: "${MEMORY_WAL_ARCHIVE_DIR:=/Users/thestudio/data/memory-main/postgres/wal_archive}"
: "${MEMORY_PG_BIN:=/opt/homebrew/opt/postgresql@16/bin}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
BASE_DIR="$MEMORY_BACKUP_DIR/base-$TS"
mkdir -p "$BASE_DIR" "$MEMORY_WAL_ARCHIVE_DIR"

export PGPASSWORD="$MEMORY_DB_PASSWORD"
"$MEMORY_PG_BIN/pg_basebackup" \
  -h "$MEMORY_DB_HOST" \
  -p "$MEMORY_DB_PORT" \
  -U "$MEMORY_DB_USER" \
  -D "$BASE_DIR" \
  -X stream \
  -c fast \
  -R

# Keep 14 daily base backups by default (portable BSD/GNU logic).
TOTAL_BASES="$(find "$MEMORY_BACKUP_DIR" -maxdepth 1 -type d -name 'base-*' | wc -l | tr -d ' ')"
if [[ "${TOTAL_BASES:-0}" -gt 14 ]]; then
  PRUNE_COUNT=$((TOTAL_BASES - 14))
  find "$MEMORY_BACKUP_DIR" -maxdepth 1 -type d -name 'base-*' | sort | head -n "$PRUNE_COUNT" | while IFS= read -r old_base; do
    [[ -n "$old_base" ]] && rm -rf "$old_base"
  done
fi

# Keep WAL archive files newer than 14 days by default.
find "$MEMORY_WAL_ARCHIVE_DIR" -type f -mtime +14 -delete

echo "backup_complete path=$BASE_DIR"
