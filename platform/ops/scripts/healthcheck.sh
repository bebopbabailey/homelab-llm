#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LITELLM_ENV_LOCAL="${LITELLM_ENV_LOCAL:-$REPO_ROOT/layer-gateway/litellm-orch/config/env.local}"
OPTILLM_ENV_FILE="${OPTILLM_ENV_FILE:-/etc/optillm-proxy/env}"
MLXCTL_BIN="${MLXCTL_BIN:-$REPO_ROOT/platform/ops/scripts/mlxctl}"
MINI_LAN_HOST="${MINI_LAN_HOST:-192.168.1.71}"
STUDIO_LAN_HOST="${STUDIO_LAN_HOST:-192.168.1.72}"

get_env_value() {
  local key="$1"
  local file="$2"
  [[ -f "$file" ]] || return 1
  local val
  val="$(grep -E "^${key}=" "$file" | tail -n1 | cut -d= -f2-)"
  [[ -n "$val" ]] || return 1
  printf "%s" "$val"
}

LITELLM_API_KEY="${LITELLM_API_KEY:-}"
if [[ -z "${LITELLM_API_KEY}" ]]; then
  LITELLM_API_KEY="$(get_env_value LITELLM_MASTER_KEY "$LITELLM_ENV_LOCAL" || true)"
fi

check_port() {
  local port="$1"
  if ss -ltn "sport = :${port}" | rg -q ":${port} "; then
    echo "port ${port}: listening"
  else
    echo "port ${port}: not listening" >&2
    return 1
  fi
}

check_http() {
  local url="$1"
  shift
  if curl -fsS --max-time 3 "$@" "$url" >/dev/null; then
    echo "http ok: ${url}"
  else
    echo "http failed: ${url}" >&2
    return 1
  fi
}

check_http_post() {
  local url="$1"
  local data="$2"
  shift 2
  if curl -fsS --max-time 5 -X POST -H "Content-Type: application/json" -d "$data" "$@" "$url" >/dev/null; then
    echo "http ok: ${url}"
  else
    echo "http failed: ${url}" >&2
    return 1
  fi
}

check_studio_mlx_lanes() {
  local ports
  ports="$("$MLXCTL_BIN" status --json | jq -r '.ports[] | select(.port >= 8100 and .port <= 8119) | select(.registry_model != "-") | .port')"
  if [[ -z "${ports}" ]]; then
    echo "no active team-lane MLX assignments detected via mlxctl status --json" >&2
    return 1
  fi
  while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    check_http "http://${STUDIO_LAN_HOST}:${p}/v1/models"
  done <<< "$ports"
}

check_port 4000
check_port 3000

if [[ -z "${LITELLM_API_KEY}" ]]; then
  echo "missing LITELLM_API_KEY (set env or update ${LITELLM_ENV_LOCAL})" >&2
  exit 1
fi

check_http "http://127.0.0.1:4000/health/readiness" -H "Authorization: Bearer ${LITELLM_API_KEY}"
check_http "http://127.0.0.1:4000/v1/models" -H "Authorization: Bearer ${LITELLM_API_KEY}"
check_http "http://${MINI_LAN_HOST}:4000/health/readiness" -H "Authorization: Bearer ${LITELLM_API_KEY}"
check_http "http://${MINI_LAN_HOST}:4000/v1/models" -H "Authorization: Bearer ${LITELLM_API_KEY}"

check_http "http://${STUDIO_LAN_HOST}:4020/v1/models"

check_http "http://127.0.0.1:8888/search?q=ping&format=json"
check_http_post "http://${MINI_LAN_HOST}:4000/v1/search/searxng-search" '{"query":"ping","max_results":1}' -H "Authorization: Bearer ${LITELLM_API_KEY}"
check_studio_mlx_lanes
