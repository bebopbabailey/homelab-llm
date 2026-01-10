#!/usr/bin/env bash
set -euo pipefail

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
  if curl -fsS --max-time 3 "$url" >/dev/null; then
    echo "http ok: ${url}"
  else
    echo "http failed: ${url}" >&2
    return 1
  fi
}

check_http_post() {
  local url="$1"
  local data="$2"
  if curl -fsS --max-time 5 -X POST -H "Content-Type: application/json" -d "$data" "$url" >/dev/null; then
    echo "http ok: ${url}"
  else
    echo "http failed: ${url}" >&2
    return 1
  fi
}

check_port 4000
check_port 3000
check_http http://127.0.0.1:4000/v1/models
check_http http://127.0.0.1:9000/health
check_http http://127.0.0.1:4020/v1/models
check_http "http://127.0.0.1:8888/search?q=ping&format=json"
check_http_post http://127.0.0.1:4000/v1/search/searxng-search '{"query":"ping","max_results":1}'
check_http http://192.168.1.72:8100/v1/models
check_http http://192.168.1.72:8101/v1/models
check_http http://192.168.1.72:8102/v1/models
check_http http://192.168.1.72:8103/v1/models
check_http http://192.168.1.72:8109/v1/models
