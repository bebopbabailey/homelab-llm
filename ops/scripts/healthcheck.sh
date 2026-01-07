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

check_port 4000
check_port 3000
check_http http://127.0.0.1:9000/health
