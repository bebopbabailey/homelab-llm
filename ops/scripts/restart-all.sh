#!/usr/bin/env bash
set -Eeuo pipefail

SERVICES=(litellm-orch open-webui ov-server optillm-proxy)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HEALTHCHECK="$REPO_ROOT/ops/scripts/healthcheck.sh"

log() { printf "\n[%s] %s\n" "$(date +'%F %T')" "$*"; }

log "Restarting services: ${SERVICES[*]}"
for svc in "${SERVICES[@]}"; do
  log "Restart: $svc"
  sudo systemctl restart "$svc.service"
done

log "Status (brief):"
for svc in "${SERVICES[@]}"; do
  sudo systemctl --no-pager --full status "$svc.service" | sed -n '1,12p' || true
done

log "Running healthcheck"
"$HEALTHCHECK"

log "All services restarted and healthy ✅"
