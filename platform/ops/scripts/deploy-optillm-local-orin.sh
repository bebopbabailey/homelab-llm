#!/usr/bin/env bash
set -Eeuo pipefail

# Deploy optillm-local from Mini (source of truth) to Orin (systemd).

ORIN_HOST="${OPTILLM_ORIN_HOST:-orin}"
REPO_DIR="/opt/homelab/optillm-local"
SYSTEMD_SERVICE="${OPTILLM_SYSTEMD_SERVICE:-optillm-local.service}"
ENV_FILE="${OPTILLM_ENV_FILE:-/etc/optillm-local/env}"
SMOKE_MODEL="${OPTILLM_SMOKE_MODEL:-}" # unused here, kept for parity

log() { printf "\n[%s] %s\n" "$(date +'%F %T')" "$*"; }
ssh_orin() { ssh -o BatchMode=yes "$ORIN_HOST" "$@"; }

log "Deploying optillm-local to $ORIN_HOST"
log "Repo: $REPO_DIR"

log "Pulling latest on Orin"
ssh_orin "cd '$REPO_DIR' && git pull --ff-only"

log "Syncing deps (uv sync if uv.lock exists)"
ssh_orin "cd '$REPO_DIR' && if [ -f uv.lock ]; then uv sync; fi"

log "Restarting systemd service: $SYSTEMD_SERVICE"
ssh_orin "sudo systemctl restart '$SYSTEMD_SERVICE'"

log "Smoke test: /v1/models"
ssh_orin "OPTILLM_API_KEY=\"\$(grep -E '^OPTILLM_API_KEY=' '$ENV_FILE' | cut -d= -f2-)\" \
  curl -fsS http://127.0.0.1:4040/v1/models \
    -H \"Authorization: Bearer \${OPTILLM_API_KEY}\" \
    | jq . >/dev/null"

log "Deploy complete"
