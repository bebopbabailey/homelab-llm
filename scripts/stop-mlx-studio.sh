#!/usr/bin/env bash
set -euo pipefail

# Stop MLX OpenAI servers (Studio) by port.
# Usage: scripts/stop-mlx-studio.sh

PORTS=(8100 8101 8102 8103)

SUDO=""
if command -v sudo >/dev/null 2>&1; then
  if sudo -n true 2>/dev/null; then
    SUDO="sudo"
  fi
fi

for port in "${PORTS[@]}"; do
  if ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Stopping process on port ${port}..."
    ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN | xargs ${SUDO} kill
    sleep 1
    if ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "Force-killing process on port ${port}..."
      ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN | xargs ${SUDO} kill -9
    fi
  else
    echo "No process found on port ${port}."
  fi
done
