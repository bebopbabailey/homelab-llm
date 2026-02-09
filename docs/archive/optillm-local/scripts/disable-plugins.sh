#!/usr/bin/env bash
set -euo pipefail

VENV="${1:-/Users/thestudio/optillm-local/.venv}"
PLUGIN_DIR="${VENV}/lib/python3.12/site-packages/optillm/plugins"

if [[ ! -d "$PLUGIN_DIR" ]]; then
  echo "Plugin dir not found: $PLUGIN_DIR" >&2
  exit 1
fi

disable() {
  local name="$1"
  local path="${PLUGIN_DIR}/${name}.py"
  if [[ -f "$path" ]]; then
    mv "$path" "${path}.disabled"
    echo "Disabled ${name}"
  fi
}

disable "router_plugin"
disable "privacy_plugin"
