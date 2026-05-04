#!/usr/bin/env bash
set -Eeuo pipefail

STUDIO_HOST="${STUDIO_HOST:-studio}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SOURCE_DIR="$REPO_ROOT/services/docs-mcp"
SERVICE_DIR="/Users/thestudio/optillm-proxy/layer-tools/docs-mcp"
WRAPPER="${STUDIO_UTILITY_WRAPPER:-$REPO_ROOT/platform/ops/scripts/studio_run_utility.sh}"
DRY_RUN=0

log() { printf '\n[%s] %s\n' "$(date +'%F %T')" "$*"; }

usage() {
  cat <<USAGE
Usage: $0 [--host <studio-host>] [--dry-run]

Syncs the monorepo docs-mcp subtree into the Studio runtime path.
Stages launchd assets, installs the firewall anchor, and restarts docs-mcp
when not running in dry-run mode.
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

if [[ ! -x "$WRAPPER" ]]; then
  echo "utility wrapper missing: $WRAPPER" >&2
  exit 2
fi

run_remote() {
  "$WRAPPER" --host "$STUDIO_HOST" -- "$1"
}

run_remote_sudo() {
  "$WRAPPER" --host "$STUDIO_HOST" --sudo -- "$1"
}

log "Preflight: ensuring target tree exists"
run_remote "mkdir -p '$SERVICE_DIR'"

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

log "Syncing docs-mcp subtree to Studio runtime path"
rsync "${RSYNC_ARGS[@]}" "$SOURCE_DIR/" "$STUDIO_HOST:$SERVICE_DIR/"

if [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run complete (no remote venv sync performed)"
  exit 0
fi

log "Syncing docs-mcp venv"
run_remote "cd '$SERVICE_DIR' && uv venv .venv && uv sync --no-dev"

log "Running Studio install/bootstrap helper"
run_remote "cd '$SERVICE_DIR' && ./scripts/studio_install.sh"

log "Staging launchd plist on Studio"
run_remote_sudo "cd '$SERVICE_DIR' && ./scripts/stage_launchd_plists.sh"

log "Installing docs-mcp firewall anchor on Studio"
run_remote_sudo "cd '$SERVICE_DIR' && ./scripts/install_docs_mcp_firewall.sh"

log "Restarting docs-mcp launchd label on Studio"
run_remote_sudo "if launchctl print system/com.bebop.docs-mcp-main >/dev/null 2>&1; then \
  launchctl kickstart -k system/com.bebop.docs-mcp-main; \
else \
  launchctl enable system/com.bebop.docs-mcp-main; \
  launchctl bootstrap system /Library/LaunchDaemons/com.bebop.docs-mcp-main.plist; \
  launchctl kickstart -k system/com.bebop.docs-mcp-main; \
fi"

log "Deploy script complete"
