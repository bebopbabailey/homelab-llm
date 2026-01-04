#!/usr/bin/env bash
set -euo pipefail

# Launch GPT-OSS 120B (MLX 6-bit) as jerry-chat on the Studio.
# Uses HF cache automatically: first run downloads, subsequent runs use cache.
# Usage: scripts/run-mlx-gptoss-architect.sh

UV_BIN="${UV_BIN:-/opt/homebrew/bin/uv}"
PROJECT_ROOT="${PROJECT_ROOT:-/opt/mlx-launch}"
MODEL_PATH="${MODEL_PATH:-halley-ai/gpt-oss-120b-MLX-6bit-gs64}"
PORT="${PORT:-8100}"
LOG_DIR="${LOG_DIR:-/tmp}"

CHAT_TEMPLATE_FILE="${CHAT_TEMPLATE_FILE:-}"

echo "Launching GPT-OSS jerry-chat model on port ${PORT}"
echo "Model path: ${MODEL_PATH}"

args=(
  run --project "${PROJECT_ROOT}" mlx-openai-server launch
  --model-path "${MODEL_PATH}"
  --model-type lm
  --host 0.0.0.0
  --port "${PORT}"
  --log-file "${LOG_DIR}/mlx-${PORT}.log"
  --log-level INFO
)

if [[ -n "${CHAT_TEMPLATE_FILE}" ]]; then
  args+=(--chat-template-file "${CHAT_TEMPLATE_FILE}")
fi

"${UV_BIN}" "${args[@]}" &

echo "Started MLX server on port ${PORT}. Log: ${LOG_DIR}/mlx-${PORT}.log"
