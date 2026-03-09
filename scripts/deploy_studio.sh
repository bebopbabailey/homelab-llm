#!/usr/bin/env bash
set -Eeuo pipefail

# Deploy optillm-proxy from Mini (source of truth) to Studio (launchd).
# - Requires the local submodule HEAD to already exist on origin
# - Checks out the exact local SHA on Studio in detached HEAD mode
# - Runs uv sync --frozen
# - Restarts launchd service
# - Runs authenticated smoke checks on Studio

REPO_DIR="/Users/thestudio/optillm-proxy"
STUDIO_HOST="${OPTILLM_STUDIO_HOST:-studio}"
LAUNCHD_LABEL="${OPTILLM_LAUNCHD_LABEL:-com.bebop.optillm-proxy}"
OPTILLM_API_KEY_ENV="${OPTILLM_API_KEY_ENV:-/etc/optillm-proxy/env}"
SMOKE_MODEL="${OPTILLM_SMOKE_MODEL:-main}"
SMOKE_APPROACH="${OPTILLM_SMOKE_APPROACH:-bon}"
SMOKE_MAX_TOKENS="${OPTILLM_SMOKE_MAX_TOKENS:-32}"
BENCH_MODEL="${OPTILLM_BENCH_MODEL:-p-plan-max}"
BENCH_PROMPT="${OPTILLM_BENCH_PROMPT:-Write a detailed migration plan with risks and rollbacks.}"
BENCH_MAX_TOKENS="${OPTILLM_BENCH_MAX_TOKENS:-1200}"
RUN_BENCH="${OPTILLM_RUN_BENCH:-0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
UTILITY_WRAPPER="${OPTILLM_STUDIO_UTILITY_WRAPPER:-$REPO_ROOT/platform/ops/scripts/studio_run_utility.sh}"
TARGET_SHA="$(git -C "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" rev-parse HEAD)"

log() { printf "\n[%s] %s\n" "$(date +'%F %T')" "$*"; }

fail() {
  log "ERROR: $*"
  exit 2
}

studio_utility() {
  local use_sudo=0
  if [[ "${1:-}" == "--sudo" ]]; then
    use_sudo=1
    shift
  fi
  if [[ ! -x "$UTILITY_WRAPPER" ]]; then
    fail "utility wrapper not executable: $UTILITY_WRAPPER"
  fi
  local cmd="$1"
  if [[ "$use_sudo" == "1" ]]; then
    "$UTILITY_WRAPPER" --host "$STUDIO_HOST" --sudo -- "$cmd"
  else
    "$UTILITY_WRAPPER" --host "$STUDIO_HOST" -- "$cmd"
  fi
}

require_local_clean() {
  git diff --quiet || fail "local tracked worktree is dirty; commit or stash before deploy"
  git diff --cached --quiet || fail "local index is dirty; commit or stash before deploy"
}

remote_require_repo() {
  studio_utility "test -d '$REPO_DIR/.git'" || fail "Studio repo is not initialized at $REPO_DIR"
}

remote_require_clean() {
  studio_utility "cd '$REPO_DIR' && git diff --quiet && git diff --cached --quiet" \
    || fail "Studio tracked worktree is dirty at $REPO_DIR"
}

remote_checkout_exact_sha() {
  studio_utility "cd '$REPO_DIR' && git fetch --all --prune && git cat-file -e '${TARGET_SHA}^{commit}' && git checkout --detach '$TARGET_SHA'"
}

remote_uv_sync() {
  studio_utility "cd '$REPO_DIR' && test -f uv.lock && uv sync --frozen"
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
  fail "launchd label '$label' not found under gui/ or system"
}

remote_optillm_api_key() {
  studio_utility "set -euo pipefail; \
    if [[ -f '$OPTILLM_API_KEY_ENV' ]]; then \
      OPTILLM_API_KEY=\"\$(grep -E '^OPTILLM_API_KEY=' '$OPTILLM_API_KEY_ENV' | cut -d= -f2-)\"; \
      test -n \"\$OPTILLM_API_KEY\"; \
      printf '%s' \"\$OPTILLM_API_KEY\"; \
      exit 0; \
    fi; \
    for domain in gui/\$(id -u) system; do \
      if launchctl print \"\$domain/$LAUNCHD_LABEL\" >/dev/null 2>&1; then \
        launchctl print \"\$domain/$LAUNCHD_LABEL\" | \
          python3 -c \"import re,sys; data=sys.stdin.read(); m=re.search(r'\\\\n\\\\s+--optillm-api-key\\\\n\\\\s+([^\\\\n]+)', data); sys.stdout.write(m.group(1).strip() if m else ''); sys.exit(0 if m and m.group(1).strip() else 1)\" && exit 0; \
      fi; \
    done; \
    exit 1" || fail "unable to resolve OPTILLM API key from $OPTILLM_API_KEY_ENV or launchd label $LAUNCHD_LABEL"
}

wait_for_http_ready() {
  local api_key="$1"
  local path="$2"
  local attempts="${3:-20}"
  local delay="${4:-1}"
  local i
  for ((i=1; i<=attempts; i++)); do
    if studio_utility "curl -fsS http://127.0.0.1:4020${path} -H \"Authorization: Bearer ${api_key}\" >/dev/null"; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

remote_models_smoke() {
  local api_key="$1"
  wait_for_http_ready "$api_key" "/v1/models" 20 1 || fail "/v1/models smoke failed after restart"
}

remote_chat_smoke() {
  local api_key="$1"
  local attempts=10
  local i
  for ((i=1; i<=attempts; i++)); do
    if studio_utility "set -euo pipefail; \
      curl -fsS http://127.0.0.1:4020/v1/chat/completions \
        -H 'Content-Type: application/json' \
        -H \"Authorization: Bearer ${api_key}\" \
        -d '{\"model\":\"'$SMOKE_MODEL'\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"optillm_approach\":\"'$SMOKE_APPROACH'\",\"max_tokens\":'$SMOKE_MAX_TOKENS'}' \
        >/dev/null"; then
      return 0
    fi
    sleep 1
  done
  fail "authenticated chat smoke failed after restart"
}

remote_bench() {
  studio_utility "set -euo pipefail; \
    test -f '$OPTILLM_API_KEY_ENV'; \
    OPTILLM_API_KEY=\"\$(grep -E '^OPTILLM_API_KEY=' '$OPTILLM_API_KEY_ENV' | cut -d= -f2-)\"; \
    test -n \"\$OPTILLM_API_KEY\"; \
    cd '$REPO_DIR' && \
    uv run scripts/bench_stream.py \
      --model '$BENCH_MODEL' \
      --prompt '$BENCH_PROMPT' \
      --max-tokens '$BENCH_MAX_TOKENS'"
}

log "Deploying optillm-proxy to $STUDIO_HOST"
log "Repo: $REPO_DIR"
log "Target SHA: $TARGET_SHA"
log "Utility wrapper: $UTILITY_WRAPPER"

require_local_clean
remote_require_repo
remote_require_clean

log "Checking out exact SHA on Studio"
remote_checkout_exact_sha

log "Syncing deps with uv sync --frozen"
remote_uv_sync

log "Restarting launchd service: $LAUNCHD_LABEL"
remote_launchd_restart "$LAUNCHD_LABEL"

log "Resolving configured API key"
OPTILLM_API_KEY="$(remote_optillm_api_key)"

log "Running /v1/models smoke"
remote_models_smoke "$OPTILLM_API_KEY"

log "Running authenticated chat smoke"
remote_chat_smoke "$OPTILLM_API_KEY"

if [[ "$RUN_BENCH" == "1" ]]; then
  log "Running benchmark on Studio"
  remote_bench
else
  log "Skipping benchmark (set OPTILLM_RUN_BENCH=1 to enable)"
fi

log "Deploy complete"
