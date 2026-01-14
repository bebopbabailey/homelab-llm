# MLX Registry and Controller (Planned)

## Purpose
Manage MLX model assignments to ports 8100-8109 on the Studio without requiring
LiteLLM reloads. This uses a registry file plus a single controller command.

## Registry
- Location (Studio): `/Users/thestudio/models/hf/hub/registry.json`
- Shape:
```json
{
  "version": 1,
  "models": {
    "jerry-xl": {
      "repo_id": "mlx-community/Qwen3-235B-A22B-Instruct-2507-6bit",
      "model_id": "mlx-community/Qwen3-235B-A22B-Instruct-2507-6bit",
      "cache_path": "/Users/thestudio/models/hf/hub/models--.../snapshots/<sha>",
      "format": "mlx",
      "port": 8100,
      "chat_template": "/path/to/chat_template.jinja",
      "tool_call_parser": "qwen3_moe",
      "reasoning_parser": "qwen3"
    }
  }
}
```

Optional fields:
- `chat_template`: passed as `--chat-template-file` if present.
- `tool_call_parser`: passed as `--tool-call-parser` if present.
- `reasoning_parser`: passed as `--reasoning-parser` if present.

## Controller (`mlxctl`)
`mlxctl` is the single command to manage MLX models. It runs locally on the
Studio and can be invoked from the Mini via SSH.

Supported commands:
- `init` — scan HF cache and initialize registry entries.
- `list` — show registered models and port assignments.
- `status` — show live ports vs registry.
- `load <model> <port>` — download/register if missing, start server, update registry.
- `unload <port>` — stop server and clear registry assignment.
- `unload-all` — stop all MLX servers and clear registry assignments.
- `reconcile` — clear registry entries for ports that are no longer listening.

## Install
Place `platform/ops/scripts/mlxctl` on both hosts and ensure it is on PATH:
```bash
ln -s /home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl /usr/local/bin/mlxctl
```

On the Studio, the script assumes:
- `mlx-openai-server` is available on PATH (or set `MLX_LAUNCH_CMD`).
- `huggingface_hub` is installed for downloads.
If `mlx-openai-server` is not on PATH, `mlxctl` will try:
`uv run --project /opt/mlx-launch mlx-openai-server launch` and then
`/opt/homebrew/bin/uv run --project /opt/mlx-launch mlx-openai-server launch`.

## Notes
- One port, one model. Ports are immutable.
- LiteLLM aliases are fixed; port swaps must keep the alias semantics consistent.
- The Studio boot model is defined in `/opt/mlx-launch/bin/start.sh` (port 8100).

## Harmony-format models (gpt-oss)
Some MLX models (e.g., gpt-oss) output Harmony tags unless a template/parser
is set. For these, set in the registry entry:
- `chat_template` to the model’s Harmony template file
- `tool_call_parser: harmony`
- `reasoning_parser: harmony`

This ensures OpenAI-compatible responses without raw `<|channel|>` tags.

## Planned Jerry Slot Mapping
Register these intents in the MLX registry (Studio):
- `jerry-xl` → `mlx-community/Qwen3-235B-A22B-Instruct-2507-6bit` (port 8100)
- `jerry-l` → `halley-ai/gpt-oss-120b-MLX-6bit-gs64` (port 8101)
- `jerry-m` → `mlx-community/DeepSeek-R1-Distill-Llama-70B-8bit` (port 8102)
- `jerry-s` → `mlx-community/Qwen2.5-Coder-32B-Instruct-8bit` (port 8103)

Bench/utility slots (ports 8104-8109) skew smaller and can be assigned later.
