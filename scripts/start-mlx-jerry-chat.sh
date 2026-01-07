#!/usr/bin/env bash
set -euo pipefail

# Start the Studio launchd service for jerry-chat (port 8100).
# Usage: scripts/start-mlx-jerry-chat.sh

STUDIO_HOST="${STUDIO_HOST:-studio}"
LAUNCHD_PLIST="/Library/LaunchDaemons/com.bebop.mlx-launch.plist"

if [[ "$(uname)" != "Darwin" ]]; then
  ssh "${STUDIO_HOST}" "sudo launchctl bootout system ${LAUNCHD_PLIST} >/dev/null 2>&1 || true; sudo launchctl bootstrap system ${LAUNCHD_PLIST}; sudo launchctl kickstart -k system/com.bebop.mlx-launch"
  exit 0
fi

sudo launchctl bootout system "${LAUNCHD_PLIST}" >/dev/null 2>&1 || true
sudo launchctl bootstrap system "${LAUNCHD_PLIST}"
sudo launchctl kickstart -k system/com.bebop.mlx-launch
