# MLX Registry and Controller (Current)

## Purpose
Keep Studio MLX inference stable and repeatable with registry-driven model mapping,
Harmony-safe parser/template defaults for GPT-OSS, and deterministic LiteLLM alias wiring.

## Runtime Reality (2026-03-01)
- Active Studio inference listeners:
  - `8100` -> `mlx-gpt-oss-120b-mxfp4-q4` (deep)
  - `8101` -> `mlx-qwen3-next-80b-mxfp4-a3b-instruct` (main)
  - `8102` -> `mlx-gpt-oss-20b-mxfp4-q4` (fast)
- Team-lane runtime command family is `vllm serve` (`vllm-metal`) under
  per-lane launchd labels:
  - `com.bebop.mlx-lane.8100`
  - `com.bebop.mlx-lane.8101`
  - `com.bebop.mlx-lane.8102`
- `mlxctl` remains the supported control plane for model/port lifecycle + gateway sync.

## Registry
- Location (Studio): `/Users/thestudio/models/hf/hub/registry.json`

Shape (abridged):
```json
{
  "version": 1,
  "models": {
    "mlx-gpt-oss-120b-mxfp4-q4": {
      "repo_id": "mlx-community/gpt-oss-120b-MXFP4-Q4",
      "model_id": "mlx-gpt-oss-120b-mxfp4-q4",
      "cache_path": "/Users/thestudio/models/hf/.../snapshots/<sha>",
      "source_path": "/Users/thestudio/models/hf/.../snapshots/<sha>",
      "format": "mlx",
      "port": 8100,
      "chat_template": "/opt/mlx-launch/templates/gpt-oss-120b-chat_template.jinja",
      "tool_call_parser": "harmony",
      "reasoning_parser": "harmony"
    }
  }
}
```

Key fields:
- `model_id`: canonical handle identity.
- `cache_path`: runtime artifact path.
- `source_path`: canonical source path (usually same as `cache_path`).
- `port`: active per-port assignment.
- `chat_template` / `tool_call_parser` / `reasoning_parser`: parser safety contract.
- `og_path` (optional): original artifact path used for conversion/offload workflows.

## Controller (`mlxctl`)
`mlxctl` is the supported command for MLX lifecycle:
- `init`, `list`, `status`, `verify`
- `ensure`, `load`, `unload`, `unload-all`, `assign-team`
- `vllm-capabilities`, `vllm-render`, `vllm-set`
- `repair-lanes`
- `sync-gateway`
- `offload-og`
- `studio-cli-sha`, `sync-studio-cli`

Backend behavior:
- Default launch backend is `vllm-metal` (`vllm serve`).
- Team-lane restart model is per-port launchd `KeepAlive` (lane-local restart).
- `mlx_lm.server` and `mlx-openai-server` are legacy fallback references only and are not part of the active runtime contract.

Source of truth contract:
- Runtime and gateway wiring are derived from registry state.
- Avoid ad-hoc edits to launch scripts for model assignment.
- Mutating commands are parity-gated against the Studio binary.
  Run `mlxctl studio-cli-sha` and, when needed, `mlxctl sync-studio-cli`.
- `mlxctl reconcile` is dry-run by default; mutation requires `--apply`.
  Stale assignment candidates are only entries with no listener, no runtime
  process, and no successful local `/v1/models` probe.

## Harmony / Parser Contract
For GPT-OSS entries, registry must keep:
- `tool_call_parser: harmony`
- `reasoning_parser: harmony`
- valid `chat_template`

For Qwen3 entries, registry must keep:
- `tool_call_parser: qwen3`
- `reasoning_parser: qwen3`
- optional discovered `chat_template`

For `vllm-metal` launch behavior, registry now supports a nested `vllm` block:
- `vllm.profile` (`qwen3_main|gpt_oss_lane|generic`)
- `vllm.tool_choice_mode` (`none|auto`)
- `vllm.tool_call_parser`, `vllm.reasoning_parser`
- `vllm.max_model_len`, `vllm.memory_fraction`, `vllm.async_scheduling`

Runtime compatibility is resolved at launch time:
- Registry keeps logical parser values (`qwen3`).
- `mlxctl` resolves runtime parser enums from current vLLM capabilities
  (for example `qwen3` -> `qwen3_xml` when required by the installed build).
- `tool_choice_mode=auto` is fail-closed: launch is blocked if the current vLLM
  binary lacks `--enable-auto-tool-choice` or a compatible tool parser.

Current staged default:
- `main` (`8101`, qwen3-next-80b) uses `tool_choice_mode=auto`.
- `deep`/`fast` remain on `tool_choice_mode=none` until explicitly changed.
- Team lanes render `VLLM_METAL_MEMORY_FRACTION=auto`.
- Team lanes require `--api-key`.
- Team lanes keep `--no-async-scheduling`.
- Paged attention is off in the current runtime contract.

`mlxctl verify` is read-only by default and catches parser/template drift.
Use `mlxctl verify --fix-defaults` only when you intentionally want defaults
persisted into registry entries.
For assigned team lanes, `verify` also fails if the lane launchd label is
disabled or unloaded.

## Gateway Sync Contract
`mlxctl sync-gateway` updates:
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/config/env.local`

Served-set source of truth:
- Handle inclusion is curated in `layer-gateway/registry/handles.jsonl`.
- Registry data enriches metadata for those served handles.

Current alias intent:
- `main` -> qwen3-next-80b (`8101`)
- `deep` -> gpt-oss-120b (`8100`)
- `fast` -> gpt-oss-20b (`8102`)
- `boost` / `boost-deep` -> Studio OptiLLM proxy (`4020`)

## Port Policy
- Team ports: `8100-8119`
- Experimental ports: `8120-8139`
- Active set currently uses only `8100/8101/8102`.
- Conservative lane defaults when registry fields are missing:
  - `8100` (`gpt-oss-120b`): `vllm_max_model_len=65536`, `vllm_memory_fraction=0.55`, `vllm_async_scheduling=false`
  - `8101` (`qwen3-next-80b`): `vllm_max_model_len=65536`, `vllm_memory_fraction=0.50`, `vllm_async_scheduling=false`
  - `8102` (`gpt-oss-20b`): `vllm_max_model_len=32768`, `vllm_memory_fraction=0.45`, `vllm_async_scheduling=false`

## Offload Policy
- Offload original artifacts only when `og_path` exists and differs from `cache_path`.
- Seagate offload remains backroom storage; only Studio/Mini-present models become active gateway handles.

## Notes
- Studio `/v1/models` may report snapshot-path IDs.
- Use registry + `mlxctl status` as canonical identity mapping.
- `mlxctl status --json` is JSON-only; add `--table` for mixed human+JSON output.
- `status=running` can be valid even when `listener_visible=false` (process is
  present; listener visibility may be delayed or restricted).
- `mlxctl status --checks` reports runtime family and runtime model path for drift triage.
- For team lanes, `status --checks` also reports `launchd_label`,
  `launchd_loaded`, `launchd_disabled`, and `http_models_ok`.
- `http_models_ok=true` is the serving-truth signal when listener visibility is
  delayed or hidden under root-owned launchd process ownership.
- `mlxctl mlx-launch-start` materializes and (re)starts per-lane launchd jobs from registry assignments.
- `mlxctl mlx-launch-start --ports` rejects partial assigned-team-lane scope unless
  `--allow-partial` is provided.
- `mlxctl mlx-launch-stop` stops per-lane launchd jobs and clears managed listeners.
- `mlxctl repair-lanes` is dry-run by default; `--apply` enables/bootstrap assigned
  team lane labels that are disabled, unloaded, or down.
- `repair-lanes` supports Mini orchestration by reading Studio registry/status
  remotely and applying launchctl steps on Studio through the sudo wrapper path.
- Output-quality gate: run `platform/ops/scripts/mlx_quality_gate.py` after
  reboot/model changes to catch protocol leakage or hangs on `fast/main/deep`.
