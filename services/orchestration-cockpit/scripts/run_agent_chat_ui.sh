#!/usr/bin/env bash
set -euo pipefail

UI_ROOT="${ORCHESTRATION_COCKPIT_UI_ROOT:-}"

if [[ -z "$UI_ROOT" ]]; then
  echo "ORCHESTRATION_COCKPIT_UI_ROOT must point at a local Agent Chat UI checkout or scaffold." >&2
  exit 1
fi

WEB_ROOT="$UI_ROOT/apps/web"
if [[ ! -d "$WEB_ROOT" ]]; then
  echo "Expected Agent Chat UI web app at $WEB_ROOT" >&2
  exit 1
fi

cd "$WEB_ROOT"
exec corepack pnpm exec next dev --hostname 127.0.0.1 --port 3030
