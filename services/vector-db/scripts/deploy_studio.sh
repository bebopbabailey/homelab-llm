#!/usr/bin/env bash
set -Eeuo pipefail

STUDIO_HOST="${STUDIO_HOST:-studio}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SOURCE_DIR="$REPO_ROOT/services/vector-db"
SERVICE_DIR="/Users/thestudio/optillm-proxy/layer-data/vector-db"
WRAPPER="${STUDIO_UTILITY_WRAPPER:-$REPO_ROOT/platform/ops/scripts/studio_run_utility.sh}"
DRY_RUN=0

log() { printf '\n[%s] %s\n' "$(date +'%F %T')" "$*"; }

if [[ ! -x "$WRAPPER" ]]; then
  echo "utility wrapper missing: $WRAPPER" >&2
  exit 2
fi

usage() {
  cat <<USAGE
Usage: $0 [--host <studio-host>] [--dry-run]

Syncs the monorepo vector-db subtree into the existing Studio runtime path.
No launchd mutation is performed.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      STUDIO_HOST="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run_remote() {
  "$WRAPPER" --host "$STUDIO_HOST" -- "$1"
}

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "source dir missing: $SOURCE_DIR" >&2
  exit 2
fi

log "Preflight: ensuring target tree exists"
run_remote "test -d '$SERVICE_DIR'"

RSYNC_ARGS=(
  -az
  --delete
  --exclude=.venv/
  --exclude=__pycache__/
  --exclude=.DS_Store
)
if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_ARGS+=(--dry-run --itemize-changes)
fi

log "Syncing monorepo vector-db subtree to Studio runtime path"
rsync "${RSYNC_ARGS[@]}" "$SOURCE_DIR/" "$STUDIO_HOST:$SERVICE_DIR/"

if [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run complete (no remote venv sync performed)"
  exit 0
fi

log "Syncing vector-db venv"
run_remote "cd '$SERVICE_DIR' && uv venv .venv && uv sync --no-dev"

log "Running Studio install/bootstrap helper"
run_remote "cd '$SERVICE_DIR' && ./scripts/studio_install.sh"

log "Deploy script complete (no launchctl mutation performed)"
