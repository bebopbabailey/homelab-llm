#!/usr/bin/env bash
set -euo pipefail

# Download and run a Hugging Face model on the Studio for quick testing.
# Usage: scripts/run-mlx-test-model.sh <repo_id> [port]
#
# Example:
#   scripts/run-mlx-test-model.sh halley-ai/gpt-oss-120b-MLX-6bit-gs64

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <repo_id> [port]"
  exit 1
fi

REPO_ID="$1"
PORT="${2:-8109}"

UV_BIN="${UV_BIN:-/opt/homebrew/bin/uv}"
PROJECT_ROOT="${PROJECT_ROOT:-/opt/mlx-launch}"

HF_HOME="${HF_HOME:-/Users/thestudio/models/hf}"
HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
HF_ASSETS_CACHE="${HF_ASSETS_CACHE:-${HF_HOME}/assets}"
HF_XET_CACHE="${HF_XET_CACHE:-${HF_HOME}/xet}"

export HF_HOME HF_HUB_CACHE HF_ASSETS_CACHE HF_XET_CACHE
export REPO_ID

echo "Downloading ${REPO_ID} to ${HF_HUB_CACHE}..."

SNAPSHOT_PATH="$(${UV_BIN} run --project "${PROJECT_ROOT}" python - <<'PY'\nimport os\nfrom huggingface_hub import snapshot_download\nrepo_id = os.environ['REPO_ID']\ncache_dir = os.environ['HF_HUB_CACHE']\npath = snapshot_download(repo_id=repo_id, cache_dir=cache_dir)\nprint(path)\nPY\n)"

echo "Snapshot path: ${SNAPSHOT_PATH}"
echo "Launching MLX server on port ${PORT}"

"${UV_BIN}" run --project "${PROJECT_ROOT}" mlx-openai-server launch \
  --model-path "${SNAPSHOT_PATH}" \
  --model-type lm \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --log-file "/tmp/mlx-${PORT}.log" \
  --log-level INFO &

echo "Started MLX server for ${REPO_ID} on port ${PORT}."
echo "Log: /tmp/mlx-${PORT}.log"
echo ""
echo "LiteLLM hint:"
echo "  Set JERRY_TEST_MODEL=openai/${SNAPSHOT_PATH}"
