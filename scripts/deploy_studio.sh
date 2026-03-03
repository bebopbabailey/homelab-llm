#!/usr/bin/env bash
set -Eeuo pipefail

# Deploy optillm-proxy from Mini (source of truth) to Studio (launchd).
# - Pushes local changes in this repo's submodule (expects you already committed)
# - Pulls on Studio
# - Runs uv sync (if uv.lock exists)
# - Applies local OptiLLM patchset into site-packages (idempotent)
# - Restarts launchd service
# - Runs smoke + optional benchmark on Studio

REPO_DIR="/Users/thestudio/optillm-proxy"
STUDIO_HOST="${OPTILLM_STUDIO_HOST:-studio}"
LAUNCHD_LABEL="${OPTILLM_LAUNCHD_LABEL:-com.bebop.optillm-proxy}"
OPTILLM_API_KEY_ENV="${OPTILLM_API_KEY_ENV:-/etc/optillm-proxy/env}"
SMOKE_MODEL="${OPTILLM_SMOKE_MODEL:-mlx-gpt-oss-120b-mxfp4-q4}"
SMOKE_APPROACH="${OPTILLM_SMOKE_APPROACH:-bon}"
SMOKE_MAX_TOKENS="${OPTILLM_SMOKE_MAX_TOKENS:-32}"
BENCH_MODEL="${OPTILLM_BENCH_MODEL:-p-plan-max}"
BENCH_PROMPT="${OPTILLM_BENCH_PROMPT:-Write a detailed migration plan with risks and rollbacks.}"
BENCH_MAX_TOKENS="${OPTILLM_BENCH_MAX_TOKENS:-1200}"
RUN_BENCH="${OPTILLM_RUN_BENCH:-0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
UTILITY_WRAPPER="${OPTILLM_STUDIO_UTILITY_WRAPPER:-$REPO_ROOT/platform/ops/scripts/studio_run_utility.sh}"

log() { printf "\n[%s] %s\n" "$(date +'%F %T')" "$*"; }

studio_utility() {
  local use_sudo=0
  if [[ "${1:-}" == "--sudo" ]]; then
    use_sudo=1
    shift
  fi
  if [[ ! -x "$UTILITY_WRAPPER" ]]; then
    log "ERROR: utility wrapper not executable: $UTILITY_WRAPPER"
    return 2
  fi
  local cmd="$1"
  if [[ "$use_sudo" == "1" ]]; then
    "$UTILITY_WRAPPER" --host "$STUDIO_HOST" --sudo -- "$cmd"
  else
    "$UTILITY_WRAPPER" --host "$STUDIO_HOST" -- "$cmd"
  fi
}

remote_launchd_restart() {
  local label="$1"
  if studio_utility "launchctl print gui/\$(id -u)/$label >/dev/null 2>&1"; then
    studio_utility "launchctl kickstart -k gui/\$(id -u)/$label"
    return 0
  fi
  if studio_utility --sudo "launchctl print system/$label >/dev/null 2>&1"; then
    studio_utility --sudo "launchctl kickstart -k system/$label"
    return 0
  fi
  log "WARN: launchd label '$label' not found under gui/ or system/."
  return 1
}

remote_uv_sync() {
  studio_utility "cd '$REPO_DIR' && if [ -f uv.lock ]; then uv sync; fi"
}

remote_preflight_repo() {
  if ! studio_utility "test -d '$REPO_DIR/.git'"; then
    log "ERROR: Studio repo is not initialized at $REPO_DIR (.git missing)."
    log "       Bootstrap the Studio working tree before running deploy_studio.sh."
    return 2
  fi
}

remote_apply_patches() {
  studio_utility "cd '$REPO_DIR' && uv run scripts/apply_optillm_patches.sh"
}

remote_smoke() {
  studio_utility "OPTILLM_API_KEY=\"\$(grep -E '^OPTILLM_API_KEY=' '$OPTILLM_API_KEY_ENV' | cut -d= -f2-)\" \
    curl -fsS http://127.0.0.1:4020/v1/chat/completions \
      -H 'Content-Type: application/json' \
      -H \"Authorization: Bearer \${OPTILLM_API_KEY}\" \
      -d '{"model":"'"$SMOKE_MODEL"'","messages":[{"role":"user","content":"ping"}],"optillm_approach":"'"$SMOKE_APPROACH"'","max_tokens":'"$SMOKE_MAX_TOKENS"'}' \
      >/dev/null"
}

remote_bench() {
  studio_utility "cd '$REPO_DIR' && \
    OPTILLM_API_KEY=\"\$(grep -E '^OPTILLM_API_KEY=' '$OPTILLM_API_KEY_ENV' | cut -d= -f2-)\" \
    uv run scripts/bench_stream.py \
      --model '$BENCH_MODEL' \
      --prompt '$BENCH_PROMPT' \
      --max-tokens '$BENCH_MAX_TOKENS'"
}

log "Deploying optillm-proxy to $STUDIO_HOST"
log "Repo: $REPO_DIR"
log "Utility wrapper: $UTILITY_WRAPPER"

log "Preflight: verifying Studio working tree"
remote_preflight_repo

log "Pulling latest on Studio"
studio_utility "cd '$REPO_DIR' && git pull --ff-only"

log "Syncing deps (uv sync if uv.lock exists)"
remote_uv_sync

log "Applying OptiLLM patchset in Studio venv"
remote_apply_patches

log "Restarting launchd service: $LAUNCHD_LABEL"
remote_launchd_restart "$LAUNCHD_LABEL"

log "Running smoke test on Studio"
remote_smoke

if [[ "$RUN_BENCH" == "1" ]]; then
  log "Running benchmark on Studio"
  remote_bench
else
  log "Skipping benchmark (set OPTILLM_RUN_BENCH=1 to enable)"
fi

log "Deploy complete"
