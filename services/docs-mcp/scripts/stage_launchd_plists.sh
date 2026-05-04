#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "stage_launchd_plists.sh must run as root" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="com.bebop.docs-mcp-main.plist"
cp "${ROOT_DIR}/launchd/${NAME}" "/Library/LaunchDaemons/${NAME}"
chown root:wheel "/Library/LaunchDaemons/${NAME}"
chmod 644 "/Library/LaunchDaemons/${NAME}"
plutil -lint "/Library/LaunchDaemons/${NAME}" >/dev/null

echo "launchd_plists_staged"
