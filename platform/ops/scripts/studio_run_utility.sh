#!/usr/bin/env bash
set -Eeuo pipefail

STUDIO_HOST="${STUDIO_HOST:-studio}"
NICE_LEVEL="${STUDIO_UTILITY_NICE:-10}"
USE_SUDO=0

usage() {
  cat <<USAGE
Usage:
  $0 [--host <studio-host>] [--sudo] [--nice <n>] -- <remote-command>

Runs a transient Studio command with utility/background scheduling clamps:
  taskpolicy -c utility -d throttle -g throttle -b + nice

Examples:
  $0 --host studio -- "cd /Users/thestudio/optillm-proxy && git pull --ff-only"
  $0 --host studio --sudo -- "launchctl print system/com.bebop.mlx-launch"
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      STUDIO_HOST="$2"
      shift 2
      ;;
    --sudo)
      USE_SUDO=1
      shift
      ;;
    --nice)
      NICE_LEVEL="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ $# -lt 1 ]]; then
  echo "Missing remote command" >&2
  usage >&2
  exit 2
fi

if [[ $# -eq 1 ]]; then
  REMOTE_COMMAND="$1"
else
  printf -v REMOTE_COMMAND '%q ' "$@"
  REMOTE_COMMAND="${REMOTE_COMMAND% }"
fi

if [[ "$USE_SUDO" == "1" ]]; then
  printf -v WRAPPED 'sudo -n taskpolicy -c utility -d throttle -g throttle -b /usr/bin/nice -n %q /bin/bash -lc %q' "$NICE_LEVEL" "$REMOTE_COMMAND"
else
  printf -v WRAPPED 'taskpolicy -c utility -d throttle -g throttle -b /usr/bin/nice -n %q /bin/bash -lc %q' "$NICE_LEVEL" "$REMOTE_COMMAND"
fi

printf -v REMOTE_SSH_CMD 'bash -lc %q' "$WRAPPED"

exec ssh \
  -o BatchMode=yes \
  -o IdentitiesOnly=yes \
  -o ControlMaster=no \
  -o ControlPath=none \
  "$STUDIO_HOST" \
  "$REMOTE_SSH_CMD"
