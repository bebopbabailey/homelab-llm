#!/usr/bin/env bash
set -euo pipefail

# Stop all MLX servers on ports 8100-8109 and boot out the Studio launchd service.
# Usage: scripts/stop-mlx-ports.sh

STUDIO_HOST="studio"
PORT_START=8100
PORT_END=8109
LAUNCHD_PLIST="/Library/LaunchDaemons/com.bebop.mlx-launch.plist"

if [[ "${1:-}" != "--local" ]] && [[ "$(uname)" != "Darwin" ]]; then
  # Run on Mini: delegate to Studio over SSH.
  ssh "${STUDIO_HOST}" "bash -s -- --local" < "${0}"
  exit 0
fi

SUDO="sudo"

if ${SUDO} launchctl print system/com.bebop.mlx-launch >/dev/null 2>&1; then
  echo "Booting out launchd service: com.bebop.mlx-launch"
  ${SUDO} launchctl bootout system "${LAUNCHD_PLIST}" || true
fi

for port in $(seq "${PORT_START}" "${PORT_END}"); do
  if ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Stopping process on port ${port}..."
    ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN | xargs ${SUDO} kill || true
    sleep 1
    if ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "Force-killing process on port ${port}..."
      ${SUDO} lsof -nP -ti -iTCP:"${port}" -sTCP:LISTEN | xargs ${SUDO} kill -9 || true
    fi
  else
    echo "No process found on port ${port}."
  fi
done

echo "Done. Ports ${PORT_START}-${PORT_END} cleared."
