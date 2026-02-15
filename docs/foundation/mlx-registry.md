# MLX Registry and Controller (Current)

## Purpose
Keep MLX inference on the Studio stable and repeatable with an Omni-first runtime:
- A single OpenAI-compatible backend (`mlx-omni-server`) serves multiple models.
- A single registry file tracks model storage paths + defaults.
- A single controller (`mlxctl`) manages downloads/conversion, the registry, and gateway wiring.

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
- `port`: legacy per-port runtime assignment (used by `mlx-openai-server`). In Omni-first mode,
  Omni ignores per-model ports; models are selected by request `model` and resolved via `cache_path`.

## Controller (`mlxctl`)
`mlxctl` is the single command to manage MLX models. It runs locally on the
Studio and can be invoked from the Mini via SSH.

Contract:
- Runtime and boot both follow the Studio MLX registry (`registry.json`).
- `mlxctl` is authoritative for changes; launchd boot should read registry
  assignments rather than hardcoded model lists.

## MLX Server Provenance (Current)
- Canonical server: `mlx-omni-server` (OpenAI-compatible)
- Launchd label (canonical): `com.bebop.mlx-omni.8100`
- Install path (canonical): `/opt/mlx-omni-launch`
- Registry (source of truth): `/Users/thestudio/models/hf/hub/registry.json`
- Legacy (disabled after cutover): `com.bebop.mlx-launch` + per-port `mlx-openai-server`

Supported commands:
- `init` — scan HF cache and initialize registry entries.
- `list` — show registered models and port assignments.
- `status` — show live ports vs registry.
- `ensure <repo>` — download and optionally convert a repo, update registry.
- `reconcile` — clear registry entries for ports that are no longer listening.
- `offload-og` — offload base-weight artifacts when they are not used for inference.
- `sync-gateway` — sync MLX registry + served handles → LiteLLM router/env.
- `omni-install|omni-stop|omni-status` — manage the canonical Omni launchd job(s).
- `omni-warm` — warm one or more models into Omni cache.

Legacy per-port commands (not used in Omni-first runtime):
- `load <model> <port>` / `unload <port>` / `unload-all`
- `assign-team`

## Install
Place `platform/ops/scripts/mlxctl` on both hosts and ensure it is on PATH:
```bash
ln -s /home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl /usr/local/bin/mlxctl
```

On the Studio, `mlxctl` supports:
- Canonical Omni mode: manages the single `mlx-omni-server` endpoint on `:8100` (see `mlxctl omni-*` commands).
- Legacy per-port mode: manages `com.bebop.mlx-launch` + per-port `mlx-openai-server` listeners.

For legacy per-port mode only, the script assumes:
- `mlx-openai-server` is available on PATH (or set `MLX_LAUNCH_CMD`).
- `huggingface_hub` is installed for downloads.
If `mlx-openai-server` is not on PATH, `mlxctl` will try:
`uv run --project /opt/mlx-launch mlx-openai-server launch` and then
`/opt/homebrew/bin/uv run --project /opt/mlx-launch mlx-openai-server launch`.

## Notes
- Canonical mode: one endpoint (`8100`) serving multiple models; the requested `model` selects which to run.
- Ports are immutable.
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
- OptiLLM proxy runs on the Studio (`:4020`) and is typically used via the LiteLLM `boost` handle.
  and include `optillm_approach` in the request body.
- Ports 8100–8119 are the team range; 8120–8139 are experimental.
- Canonical boot is the Omni launchd job for `:8100` (`com.bebop.mlx-omni.8100`).
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

Sync order is: MLX registry (Studio) → gateway router/env (Mini).
- When run from the Studio, it SSHes to `GATEWAY_HOST` (default: `mini`) and
  uses `GATEWAY_MLXCTL` (default: `/home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl`).
- Gateway sync uses `MLX_HOST` (default: `192.168.1.72`) for generated API base URLs.
- **Alias-only model list:** `router.yaml` exposes only alias handles (e.g. `main/deep/fast/swap`).
  Canonical `mlx-*` model IDs remain in the MLX registry + env vars but are omitted from
  LiteLLM’s `/v1/models` list to avoid duplicate entries in clients.

Omni-first served-set:
- `layer-gateway/registry/handles.jsonl` is treated as the curated list of MLX handles that are exposed.
- `sync-gateway` does **not** rewrite `handles.jsonl`.
- A handle is considered "served by MLX" when its `endpoint_ref` starts with:
  - `ep_mlx_omni_` (canonical), or
  - `ep_mlx_slot_` (legacy transition)
- Env generation prefers `MLX_SINGLE_API_BASE` when set; otherwise it uses `MLX_HOST` and the port parsed from
  `endpoint_ref` (default Omni port: `MLX_OMNI_PORT`, default `8100`).

## Harmony-format models (gpt-oss)
Some MLX models (e.g., gpt-oss) output Harmony tags unless a template/parser
is set. For these, set in the registry entry:
- `chat_template` to the model’s Harmony template file
- `tool_call_parser: harmony`
- `reasoning_parser: harmony`
If short prompts return `reasoning_content` without `content`, increase
`max_tokens` or set a lower `reasoning_effort` via `request_params`.

`mlxctl` now auto-applies and persists these fields for `gpt-oss*` entries
when running `init`, `ensure`, `load`, and `verify`:
- `tool_call_parser: harmony`
- `reasoning_parser: harmony`
- `chat_template` resolved from `MLX_TEMPLATE_DIR` (default:
  `/opt/mlx-launch/templates`) using GPT-OSS 20B/120B template fallbacks.

`mlxctl verify` is now strict for GPT-OSS entries and fails if Harmony parser
fields are missing or the `chat_template` path does not exist.

For `qwen3*` entries, `mlxctl` auto-applies:
- `tool_call_parser: qwen3`
- `reasoning_parser: qwen3`
- optional `chat_template` from the model snapshot when available

`mlxctl verify` is strict for Qwen3 parser fields and also checks runtime
parity (registry `cache_path` must match the live `--model-path` on assigned
ports).

Studio note (2026-01-30):
- GPT‑OSS 20B snapshot lacks `chat_template.jinja`. We supply a supported override:
  `/opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja`.
- For GPT‑OSS handles, a higher `max_tokens` (>= 256) ensures `content` is emitted
  alongside `reasoning_content`.

This ensures OpenAI-compatible responses without raw `<|channel|>` tags.

## Current Boot (Canonical)
The canonical MLX endpoint is Omni on port `8100`:
- Base URL: `http://192.168.1.72:8100/v1`
- Model selection is via the `model` field (e.g. `openai/mlx-qwen3-next-80b-mxfp4-a3b-instruct`).

## Port policy
Omni-first does not require per-model ports:
- Use `mlxctl ensure <hf_repo_id>` to download/convert/register a model.
- Test by calling Omni with `model=<model_id>` (Omni lazy-loads on first request).
- Keep the hot set warm using `MLX_OMNI_PREWARM_MODELS` and/or `mlxctl omni-warm`.
