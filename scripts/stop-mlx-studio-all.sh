#!/usr/bin/env bash
set -euo pipefail

# Stop MLX model servers on ports 8100-8109 and prevent launchd respawn.
# Usage: scripts/stop-mlx-studio-all.sh

LAUNCHD_PLIST="/Library/LaunchDaemons/com.bebop.mlx-launch.plist"
PORT_START=8100
PORT_END=8109

SUDO=""
if command -v sudo >/dev/null 2>&1; then
  if sudo -n true 2>/dev/null; then
    SUDO="sudo"
  else
    SUDO="sudo"
  fi
fi

if [[ -n "${SUDO}" ]]; then
  if ${SUDO} launchctl print system/com.bebop.mlx-launch >/dev/null 2>&1; then
    echo "Stopping launchd service: com.bebop.mlx-launch"
    ${SUDO} launchctl bootout system "${LAUNCHD_PLIST}" || true
  fi
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

echo "Done. Launchd is booted out; ports ${PORT_START}-${PORT_END} cleared."
