#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "stage_launchd_plists.sh must run as root" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for name in com.bebop.elasticsearch-memory-main.plist com.bebop.memory-api-main.plist com.bebop.kibana-memory-main.plist; do
  cp "${ROOT_DIR}/launchd/${name}" "/Library/LaunchDaemons/${name}"
  chown root:wheel "/Library/LaunchDaemons/${name}"
  chmod 644 "/Library/LaunchDaemons/${name}"
  plutil -lint "/Library/LaunchDaemons/${name}" >/dev/null
done

echo "launchd_plists_staged"
