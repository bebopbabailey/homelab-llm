#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="${HOME}/.config/opencode"
CONFIG_FILE="${CONFIG_DIR}/opencode.json"
KEY_FILE="${CONFIG_DIR}/litellm_api_key"

probe_url() {
  local url="$1"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 4 "${url}/models" || true)"
  [[ "${code}" != "000" ]]
}

if [[ -n "${OPENCODE_LITELLM_BASE_URL:-}" ]]; then
  BASE_URL="${OPENCODE_LITELLM_BASE_URL}"
else
  BASE_URL=""
  for candidate in \
    "https://gateway.tailfd1400.ts.net/v1" \
    "http://100.69.99.60:4443/v1" \
    "http://127.0.0.1:4000/v1"
  do
    if probe_url "${candidate}"; then
      BASE_URL="${candidate}"
      break
    fi
  done
  if [[ -z "${BASE_URL}" ]]; then
    BASE_URL="http://127.0.0.1:4000/v1"
  fi
fi

mkdir -p "${CONFIG_DIR}"

if [[ -f "${CONFIG_FILE}" ]]; then
  BACKUP_FILE="${CONFIG_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
  cp "${CONFIG_FILE}" "${BACKUP_FILE}"
  echo "backed up existing config -> ${BACKUP_FILE}"
fi

cat > "${CONFIG_FILE}" <<JSON
{
  "\$schema": "https://opencode.ai/config.json",
  "provider": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LiteLLM (homelab)",
      "options": {
        "baseURL": "${BASE_URL}",
        "apiKey": "{file:~/.config/opencode/litellm_api_key}"
      },
      "models": {
        "main": { "name": "Main" },
        "deep": { "name": "Deep" },
        "fast": { "name": "Fast" },
        "boost": { "name": "Boost" },
        "boost-plan": { "name": "Boost Plan" },
        "boost-plan-verify": { "name": "Boost Plan Verify" },
        "boost-ideate": { "name": "Boost Ideate" },
        "boost-fastdraft": { "name": "Boost Fastdraft" }
      }
    }
  },
  "model": "litellm/boost-plan",
  "small_model": "litellm/boost-fastdraft",
  "permission": {
    "bash": "ask",
    "edit": "ask"
  }
}
JSON
chmod 0600 "${CONFIG_FILE}"

if [[ ! -f "${KEY_FILE}" ]]; then
  touch "${KEY_FILE}"
  chmod 0600 "${KEY_FILE}"
  echo "created empty key file -> ${KEY_FILE}"
  echo "populate it with your LiteLLM key before running OpenCode."
else
  chmod 0600 "${KEY_FILE}"
fi

cat <<EOF
OpenCode config written:
  ${CONFIG_FILE}

Base URL:
  ${BASE_URL}

Next checks:
  opencode models litellm
  opencode run -m litellm/boost-plan "Reply with exactly: plan-ok"
EOF
