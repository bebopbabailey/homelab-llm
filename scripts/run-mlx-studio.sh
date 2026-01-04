#!/usr/bin/env bash
set -euo pipefail

# Launch MLX OpenAI servers (Studio) with local HF cache snapshots.
# Usage: scripts/run-mlx-studio.sh

UV_BIN="${UV_BIN:-/opt/homebrew/bin/uv}"
PROJECT_ROOT="${PROJECT_ROOT:-/opt/mlx-launch}"

MODEL_7B="/Users/thestudio/models/hf/hub/models--mlx-community--Qwen2.5-Coder-7B-Instruct-8bit/snapshots/b292f3cb59a1dea859013fad96af2640ce15ba9e"
MODEL_32B="/Users/thestudio/models/hf/hub/models--mlx-community--Qwen2.5-Coder-32B-Instruct-8bit/snapshots/64350339cd0f9e1c4ede301e986ad458410b4e6f"
MODEL_70B="/Users/thestudio/models/hf/hub/models--mlx-community--DeepSeek-R1-Distill-Llama-70B-8bit/snapshots/de2b398d70a39b0a378900e9855162191ae4515a"

LOG_DIR="${LOG_DIR:-/tmp}"
TEMPLATE_DIR="${TEMPLATE_DIR:-/Users/thestudio/models/chat_templates}"
TEMPLATE_7B="${TEMPLATE_DIR}/qwen7b.jinja"
TEMPLATE_32B="${TEMPLATE_DIR}/qwen32b.jinja"
TEMPLATE_70B="${TEMPLATE_DIR}/deepseek70b.jinja"

echo "Launching MLX servers with uv project: ${PROJECT_ROOT}"

"${UV_BIN}" run --project "${PROJECT_ROOT}" mlx-openai-server launch \
  --model-path "${MODEL_7B}" --model-type lm --trust-remote-code \
  --chat-template-file "${TEMPLATE_7B}" \
  --host 0.0.0.0 --port 8103 \
  --log-file "${LOG_DIR}/mlx-8103.log" --log-level INFO &

"${UV_BIN}" run --project "${PROJECT_ROOT}" mlx-openai-server launch \
  --model-path "${MODEL_32B}" --model-type lm --trust-remote-code \
  --chat-template-file "${TEMPLATE_32B}" \
  --host 0.0.0.0 --port 8101 \
  --log-file "${LOG_DIR}/mlx-8101.log" --log-level INFO &

"${UV_BIN}" run --project "${PROJECT_ROOT}" mlx-openai-server launch \
  --model-path "${MODEL_70B}" --model-type lm --trust-remote-code \
  --chat-template-file "${TEMPLATE_70B}" \
  --host 0.0.0.0 --port 8102 \
  --log-file "${LOG_DIR}/mlx-8102.log" --log-level INFO &

echo "Started MLX servers on ports 8103, 8101, 8102."
echo "Logs: ${LOG_DIR}/mlx-8103.log, ${LOG_DIR}/mlx-8101.log, ${LOG_DIR}/mlx-8102.log"
