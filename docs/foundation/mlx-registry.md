# MLX Registry and Controller (Planned)

## Purpose
Manage MLX model assignments to ports 8100-8139 on the Studio without requiring
LiteLLM reloads. This uses a registry file plus a single controller command.

## Registry
- Location (Studio): `/Users/thestudio/models/hf/hub/registry.json`
- Shape:
```json
{
  "version": 1,
  "models": {
    "mlx-qwen3-235b-a22b-instruct-2507-6bit": {
      "repo_id": "mlx-community/Qwen3-235B-A22B-Instruct-2507-6bit",
      "model_id": "mlx-qwen3-235b-a22b-instruct-2507-6bit",
      "cache_path": "/Users/thestudio/models/hf/hub/models--.../snapshots/<sha>",
      "source_path": "/Users/thestudio/models/hf/hub/models--.../snapshots/<sha>",
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
- `source_path`: canonical source path for the model artifact (default: initial cache_path).
- `og_path`: base-weight path used only during conversion; if set and different from `cache_path`,
  it can be offloaded once the model is not serving inference.

## Controller (`mlxctl`)
`mlxctl` is the single command to manage MLX models. It runs locally on the
Studio and can be invoked from the Mini via SSH.

## MLX Server Provenance (Required)
- Upstream repo: https://github.com/cubist38/mlx-openai-server
- Fork (if any): none detected (installed from upstream)
- Pin/version: 1.5.1 (pyproject.toml)
- Install path: `/opt/mlx-launch` (uv/venv + install steps)
- Boot entrypoint: `/opt/mlx-launch/bin/start.sh`
- Local patches: none (use supported Harmony parsers + templates)

Supported commands:
- `init` — scan HF cache and initialize registry entries.
- `list` — show registered models and port assignments.
- `status` — show live ports vs registry.
- `load <model> <port>` — download/register if missing, start server, update registry.
- `ensure <repo>` — download and optionally convert a repo, update registry.
- `unload <port>` — stop server and clear registry assignment.
- `unload-all` — stop all MLX servers and clear registry assignments.
- `reconcile` — clear registry entries for ports that are no longer listening.
- `offload-og` — offload base-weight artifacts when they are not used for inference.
- `sync-gateway` — sync MLX registry → LiteLLM router/env/handles.
- `assign-team` — assign all current MLX models to team ports.

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
- Only models present on the Studio are exposed via LiteLLM handles; Seagate is backroom storage only.
- Naming: `mlxctl` defaults to canonical model IDs in the form
  `mlx-<family>-<params>-<quant>-<variant>` (dash-only, no org prefix).
  Order is fixed: family → parameter count → quant → other identifiers.
  Use `--name` only for exceptions.
- LiteLLM `router.yaml` uses MLX registry fields:
  `context_length` → `max_input_tokens` and `max_output_tokens` (currently 65k).
  Defaults persist in the Studio registry and are synced by `mlxctl sync-gateway`.
- Current routing mode: MLX handles route **directly** to MLX ports.
- OptiLLM is used only when clients call `http://127.0.0.1:4020/v1` directly
  and include `optillm_approach` in the request body.
- Ports 8100–8119 are the team range; 8120–8139 are experimental.
- The Studio boot ensemble is defined in `/opt/mlx-launch/bin/start.sh`
  (current ports: `8100`, `8101`, `8102`).
- Offload happens only when `og_path` is set and `og_path != cache_path`.
  This prevents removing artifacts that are used for inference.
- `mlxctl list` now shows `context_length` and `max_output_tokens`.
- `mlxctl load` / `mlxctl ensure` set defaults if missing:
  - `context_length`: inferred from `config.json` when available, else 131072
  - `max_output_tokens`: defaults to 64000
- `mlxctl ensemble` is deprecated (use `load`/`assign-team`).

## Conversion + offload defaults
- `mlxctl load` and `mlxctl ensure` use `--convert auto` by default:
  - If the repo looks pre-converted (e.g., `mlx-community`), no conversion is attempted.
  - Otherwise a local conversion runs and the converted output is stored under the HF cache.
- Converted entries set `og_path` to the base repo cache directory and `cache_path` to the converted output.
- Offload runs by default after a conversion and moves the base repo cache to `/mnt/seagate/og_models/mlx-hf`.
- Override conversion with `--convert force|skip` and offload with `--no-offload-og`.
- Override pre-converted detection with `--preconverted yes|no|auto`.
- Conversion command is configurable via `MLX_CONVERT_CMD`. Default:
  `python3 -m mlx_lm.convert --hf-path {src} --mlx-path {dest}`
  Placeholders: `{repo}` `{src}` `{dest}`.
- Pre-converted detection uses `MLX_PRECONVERTED_ORGS` (default: `mlx-community,mlx,ml-explore`)
  and `MLX_PRECONVERTED_HINTS` (default: `mlx`) for repo name matches.
- When running `mlxctl offload-og` from the Studio, it will SSH to `MLX_OFFLOAD_HOST`
  (default: `mini`) so the offload script runs where the Seagate drive is attached.
- Registry entries may include `request_params` to inject default LiteLLM params
  when syncing to `router.yaml` (e.g., `reasoning_effort: low` for GPT-OSS models).

## Gateway sync
`mlxctl sync-gateway` updates:
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/config/env.local`
- `layer-gateway/registry/handles.jsonl`

Sync order is: model service → MLX registry → gateway router/env → handles registry.
- When run from the Studio, it SSHes to `GATEWAY_HOST` (default: `mini`) and
  uses `GATEWAY_MLXCTL` (default: `/home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl`).
- Gateway sync uses `MLX_HOST` (default: `192.168.1.72`) for generated API base URLs.

## Harmony-format models (gpt-oss)
Some MLX models (e.g., gpt-oss) output Harmony tags unless a template/parser
is set. For these, set in the registry entry:
- `chat_template` to the model’s Harmony template file
- `tool_call_parser: harmony`
- `reasoning_parser: harmony`
If short prompts return `reasoning_content` without `content`, increase
`max_tokens` or set a lower `reasoning_effort` via `request_params`.

Studio note (2026-01-30):
- GPT‑OSS 20B snapshot lacks `chat_template.jinja`. We supply a supported override:
  `/opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja`.
- For GPT‑OSS handles, a higher `max_tokens` (>= 256) ensures `content` is emitted
  alongside `reasoning_content`.

This ensures OpenAI-compatible responses without raw `<|channel|>` tags.

## Current Boot Ensemble
The boot ensemble is the **source-of-truth** for default MLX availability.
Current boot ensemble:
- `mlx-gpt-oss-120b-mxfp4-q4` → port `8100`
- `mlx-gemma-3-27b-it-qat-4bit` → port `8101`
- `mlx-gpt-oss-20b-mxfp4-q4` → port `8102`

## Port policy
- New downloads intended for testing should load into the lowest available
  experimental port (8120–8139). Use `mlxctl load <model> auto`.
- Team models are promoted into 8100–8119 explicitly by choosing the port.
  `mlxctl assign-team` orders by on-disk size.
