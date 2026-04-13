#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
APP_DIR="${REPO_ROOT}/services/searxng/app"
SETTINGS_SRC="${REPO_ROOT}/services/searxng/settings.yml.example"
SETTINGS_DIR="/etc/searxng"
SETTINGS_DST="${SETTINGS_DIR}/settings.yml"
ENV_DST="${SETTINGS_DIR}/env"

if [[ ! -d "${APP_DIR}" ]]; then
  echo "Missing SearXNG checkout at ${APP_DIR}" >&2
  exit 1
fi

cd "${APP_DIR}"
uv venv .venv
uv pip install -r requirements.txt -r requirements-server.txt

sudo mkdir -p "${SETTINGS_DIR}"
if [[ ! -f "${SETTINGS_DST}" ]]; then
  sudo cp "${SETTINGS_SRC}" "${SETTINGS_DST}"
  secret="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  sudo sed -i "s/change-me/${secret}/" "${SETTINGS_DST}"
fi

if [[ ! -f "${ENV_DST}" ]]; then
  sudo cp "${REPO_ROOT}/services/searxng/searxng.env.example" "${ENV_DST}"
fi

echo "SearXNG bootstrap complete."
