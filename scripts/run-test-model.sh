#!/usr/bin/env bash
set -euo pipefail

# Download (if needed) and run a Hugging Face model on port 8109 (Studio),
# then update LiteLLM config on the Mini and restart the service.
# Usage: scripts/run-test-model.sh <repo_id> [port]

if [[ "${1:-}" == "--local" ]]; then
  shift
  REPO_ID="${1:-}"
  PORT="${2:-8109}"
  HF_HOME_STUDIO="${3:-/Users/thestudio/models/hf}"
  HF_HUB_CACHE_STUDIO="${HF_HOME_STUDIO}/hub"

  if [[ -z "${REPO_ID}" ]]; then
    echo "Usage (local): $0 --local <repo_id> [port] [hf_home]"
    exit 1
  fi

  export HF_HOME="${HF_HOME_STUDIO}"
  export HF_HUB_CACHE="${HF_HUB_CACHE_STUDIO}"
  export HF_ASSETS_CACHE="${HF_HOME_STUDIO}/assets"
  export HF_XET_CACHE="${HF_HOME_STUDIO}/xet"
  export REPO_ID="${REPO_ID}"

  UV_BIN="${UV_BIN:-/opt/homebrew/bin/uv}"
  PROJECT_ROOT="${PROJECT_ROOT:-/opt/mlx-launch}"

  repo_slug="${REPO_ID//\//--}"
  cache_root="${HF_HUB_CACHE}/models--${repo_slug}/snapshots"

  if [[ -d "${cache_root}" ]] && [[ -n "$(ls -A "${cache_root}" 2>/dev/null)" ]]; then
    SNAPSHOT_PATH="$(ls -dt "${cache_root}"/* | head -n1)"
    echo "Using cached snapshot: ${SNAPSHOT_PATH}"
  else
    echo "Downloading ${REPO_ID} to ${HF_HUB_CACHE}..."
    SNAPSHOT_PATH="$(
      ${UV_BIN} run --project "${PROJECT_ROOT}" python - <<'PY'
import os
from huggingface_hub import snapshot_download

repo_id = os.environ["REPO_ID"]
cache_dir = os.environ["HF_HUB_CACHE"]
path = snapshot_download(repo_id=repo_id, cache_dir=cache_dir)
print(path)
PY
    )"
  fi

  echo "Snapshot path: ${SNAPSHOT_PATH}"

  if lsof -nP -ti -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port ${PORT} is in use; stopping existing process..."
    lsof -nP -ti -iTCP:"${PORT}" -sTCP:LISTEN | xargs kill || true
    sleep 1
  fi

  echo "Launching MLX server on port ${PORT}"
  "${UV_BIN}" run --project "${PROJECT_ROOT}" mlx-openai-server launch \
    --model-path "${SNAPSHOT_PATH}" \
    --model-type lm \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --log-file "/tmp/mlx-${PORT}.log" \
    --log-level INFO &

  echo "SNAPSHOT_PATH=${SNAPSHOT_PATH}"
  exit 0
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <repo_id> [port]"
  exit 1
fi

REPO_ID="$1"
PORT="${2:-8109}"
STUDIO_HOST="studio"
STUDIO_API_HOST="192.168.1.72"
MINI_HOST="mini"

HF_HOME_STUDIO="/Users/thestudio/models/hf"

update_litellm() {
  local snapshot_path="$1"
  local api_base="http://${STUDIO_API_HOST}:${PORT}/v1"
  local model="openai/${snapshot_path}"

  python3 - <<PY
from pathlib import Path
import re

env_path = Path("config/env.local")
text = env_path.read_text()

def upsert(key, value):
    global text
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if pattern.search(text):
        text = pattern.sub(f"{key}={value}", text)
    else:
        text = text.rstrip() + f"\\n{key}={value}\\n"

upsert("JERRY_TEST_API_BASE", "${api_base}")
upsert("JERRY_TEST_MODEL", "${model}")
upsert("JERRY_TEST_API_KEY", "dummy")

env_path.write_text(text)
PY

  echo "Updated config/env.local:"
  echo "  JERRY_TEST_MODEL=${model}"
  echo "  JERRY_TEST_API_BASE=${api_base}"

  sudo systemctl restart litellm-orch
  echo "Restarted litellm-orch"
}

if [[ "$(uname)" == "Darwin" ]]; then
  # Run locally on Studio, then update LiteLLM on the Mini via SSH.
  SNAPSHOT_PATH="$("${0}" --local "${REPO_ID}" "${PORT}" "${HF_HOME_STUDIO}" | grep -E '^SNAPSHOT_PATH=' | tail -n1 | cut -d= -f2-)"
  if [[ -z "${SNAPSHOT_PATH}" ]]; then
    echo "Failed to capture snapshot path on Studio."
    exit 1
  fi

  ssh "${MINI_HOST}" 'bash -s' <<PY
cd ~/litellm-orch
python3 - <<'PYY'
from pathlib import Path
import re

snapshot = "${SNAPSHOT_PATH}"
api_base = "http://${STUDIO_API_HOST}:${PORT}/v1"
model = f"openai/{snapshot}"
path = Path("config/env.local")
text = path.read_text()

def upsert(key, value):
    global text
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if pattern.search(text):
        text = pattern.sub(f"{key}={value}", text)
    else:
        text = text.rstrip() + f"\\n{key}={value}\\n"

upsert("JERRY_TEST_API_BASE", api_base)
upsert("JERRY_TEST_MODEL", model)
upsert("JERRY_TEST_API_KEY", "dummy")
path.write_text(text)
PYY
sudo systemctl restart litellm-orch
PY
  exit 0
fi

REMOTE_OUTPUT="$(ssh "${STUDIO_HOST}" "bash -s -- --local '${REPO_ID}' '${PORT}' '${HF_HOME_STUDIO}'" < "${0}")"
echo "${REMOTE_OUTPUT}"

SNAPSHOT_PATH="$(printf '%s\n' "${REMOTE_OUTPUT}" | grep -E '^SNAPSHOT_PATH=' | tail -n1 | cut -d= -f2-)"
if [[ -z "${SNAPSHOT_PATH}" ]]; then
  echo "Failed to capture snapshot path from Studio."
  exit 1
fi

update_litellm "${SNAPSHOT_PATH}"
