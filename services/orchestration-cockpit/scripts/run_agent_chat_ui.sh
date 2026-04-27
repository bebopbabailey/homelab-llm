#!/usr/bin/env bash
set -euo pipefail

UI_ROOT="${ORCHESTRATION_COCKPIT_UI_ROOT:-$HOME/.local/share/orchestration-cockpit/agent-chat-ui}"
UI_HOST="${ORCHESTRATION_COCKPIT_UI_HOST:-127.0.0.1}"
UI_PORT="${ORCHESTRATION_COCKPIT_UI_PORT:-3030}"
NEXT_BIN="${ORCHESTRATION_COCKPIT_NEXT_BIN:-}"
COREPACK_BIN="${ORCHESTRATION_COCKPIT_COREPACK_BIN:-$(command -v corepack 2>/dev/null || true)}"
PNPM_BIN="${ORCHESTRATION_COCKPIT_PNPM_BIN:-$(command -v pnpm 2>/dev/null || true)}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:2024}"
export NEXT_PUBLIC_ASSISTANT_ID="${NEXT_PUBLIC_ASSISTANT_ID:-operator-cockpit}"
export PORT="${PORT:-$UI_PORT}"

if [[ -z "$UI_ROOT" ]]; then
  echo "ORCHESTRATION_COCKPIT_UI_ROOT must point at a local Agent Chat UI checkout or scaffold." >&2
  exit 1
fi

WEB_ROOT="$UI_ROOT/apps/web"
if [[ ! -d "$WEB_ROOT" ]]; then
  echo "Expected Agent Chat UI web app at $WEB_ROOT" >&2
  exit 1
fi
if [[ -z "$NEXT_BIN" ]]; then
  NEXT_BIN="$WEB_ROOT/node_modules/.bin/next"
fi
cd "$WEB_ROOT"
if [[ -n "$NEXT_BIN" && -x "$NEXT_BIN" ]]; then
  exec "$NEXT_BIN" dev --hostname "$UI_HOST" --port "$UI_PORT"
fi
if [[ -n "$COREPACK_BIN" && -x "$COREPACK_BIN" ]]; then
  exec "$COREPACK_BIN" pnpm exec next dev --hostname "$UI_HOST" --port "$UI_PORT"
fi
if [[ -n "$PNPM_BIN" && -x "$PNPM_BIN" ]]; then
  exec "$PNPM_BIN" exec next dev --hostname "$UI_HOST" --port "$UI_PORT"
fi

echo "Expected next, corepack, or pnpm launcher via ORCHESTRATION_COCKPIT_NEXT_BIN, ORCHESTRATION_COCKPIT_COREPACK_BIN, or ORCHESTRATION_COCKPIT_PNPM_BIN" >&2
exit 1
