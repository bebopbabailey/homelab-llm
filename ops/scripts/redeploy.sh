#!/usr/bin/env bash
set -Eeuo pipefail

# -----------------------------------------------------------------------------
# redeploy.sh
# Safe-ish deploy helper for a systemd + uv monorepo.
#
# What it does:
#  - verifies you're in a git repo
#  - pulls latest changes
#  - optionally runs `uv sync` if the service directory has a pyproject + lock
#  - restarts requested systemd services
#  - runs a health check
#
# Usage:
#   ./ops/scripts/redeploy.sh all
#   ./ops/scripts/redeploy.sh litellm-orch
#   ./ops/scripts/redeploy.sh open-webui ov-server
#
# Notes:
#  - requires passwordless sudo for systemctl (recommended) OR you'll be prompted
#  - does not delete anything, does not migrate state
# -----------------------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HEALTHCHECK="$REPO_ROOT/ops/scripts/healthcheck.sh"

# Services we know how to manage.
KNOWN_SERVICES=("litellm-orch" "open-webui" "ov-server" "optillm-proxy")

log() { printf "\n[%s] %s\n" "$(date +'%F %T')" "$*"; }
die() { printf "\nERROR: %s\n" "$*" >&2; exit 1; }

is_known_service() {
  local svc="$1"
  for s in "${KNOWN_SERVICES[@]}"; do
    [[ "$svc" == "$s" ]] && return 0
  done
  return 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

service_dir() {
  local svc="$1"
  case "$svc" in
    litellm-orch) echo "$REPO_ROOT/layer-gateway/litellm-orch" ;;
    optillm-proxy) echo "$REPO_ROOT/layer-gateway/optillm-proxy" ;;
    open-webui) echo "$REPO_ROOT/layer-interface/open-webui" ;;
    ov-server) echo "$REPO_ROOT/layer-inference/ov-llm-server" ;;
    *) echo "$REPO_ROOT/$svc" ;;
  esac
}

maybe_uv_sync() {
  # We only sync if:
  #  - service dir exists
  #  - has pyproject.toml
  #  - and has a uv lock (uv.lock) or requirements lock (we treat uv.lock as best)
  local svc="$1"
  local svc_dir
  svc_dir="$(service_dir "$svc")"
  [[ -d "$svc_dir" ]] || return 0

  if [[ -f "$svc_dir/pyproject.toml" ]]; then
    if [[ -f "$svc_dir/uv.lock" ]]; then
      if command -v uv >/dev/null 2>&1; then
        log "uv.lock found for $svc → running 'uv sync' in $svc_dir"
        (cd "$svc_dir" && uv sync)
      else
        log "uv.lock found for $svc but 'uv' not on PATH → skipping uv sync"
        log "Tip: add uv to PATH or call it via absolute path"
      fi
    else
      log "pyproject.toml found for $svc but no uv.lock → skipping uv sync"
      log "Tip: add uv.lock for reproducible deps if you want this automated"
    fi
  fi
}

restart_service() {
  local svc="$1"
  log "Restarting systemd service: $svc"
  sudo systemctl restart "$svc.service"
  sudo systemctl --no-pager --full status "$svc.service" | sed -n '1,12p' || true
}

usage() {
  cat <<EOF
Usage:
  $0 all
  $0 <service> [service2 ...]
Known services: ${KNOWN_SERVICES[*]}

Examples:
  $0 all
  $0 litellm-orch
  $0 open-webui ov-server
EOF
}

main() {
  require_cmd git
  require_cmd sudo
  require_cmd systemctl

  [[ -d "$REPO_ROOT/.git" ]] || die "Not a git repo: $REPO_ROOT"
  [[ -x "$HEALTHCHECK" ]] || die "Missing or non-executable healthcheck: $HEALTHCHECK"

  if [[ $# -lt 1 ]]; then
    usage
    exit 2
  fi

  local targets=()

  if [[ "$1" == "all" ]]; then
    targets=("${KNOWN_SERVICES[@]}")
  else
    for arg in "$@"; do
      is_known_service "$arg" || die "Unknown service: $arg (known: ${KNOWN_SERVICES[*]})"
      targets+=("$arg")
    done
  fi

  log "Repo root: $REPO_ROOT"
  log "Targets: ${targets[*]}"

  # Make sure we don't have uncommitted local changes that will cause pull conflicts.
  if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
    log "WARNING: repo has uncommitted changes:"
    git -C "$REPO_ROOT" status --porcelain
    log "I will NOT pull until you commit/stash/clean. Exiting."
    exit 1
  fi

  log "Pulling latest changes"
  git -C "$REPO_ROOT" pull --ff-only

  # Sync deps per service if possible (safe no-op if no locks).
  for svc in "${targets[@]}"; do
    maybe_uv_sync "$svc"
  done

  # Restart services.
  for svc in "${targets[@]}"; do
    restart_service "$svc"
  done

  # Final health check
  log "Running healthcheck"
  "$HEALTHCHECK"

  log "Redeploy complete ✅"
}

main "$@"
