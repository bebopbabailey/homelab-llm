# MLX Registry and Controller (Current)

## Purpose
Keep Studio MLX inference stable and repeatable with registry-driven model mapping,
Harmony-safe parser/template defaults for GPT-OSS, and deterministic LiteLLM alias wiring.

## Runtime Reality (2026-02-27)
- Active Studio inference listeners:
  - `8100` -> `mlx-gpt-oss-120b-mxfp4-q4` (deep)
  - `8101` -> `mlx-qwen3-next-80b-mxfp4-a3b-instruct` (main)
  - `8102` -> `mlx-gpt-oss-20b-mxfp4-q4` (fast)
- Team-lane runtime command family is `vllm serve` (`vllm-metal`) under
  `com.bebop.mlx-launch` (`8100-8119`).
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
- `sync-gateway`
- `offload-og`

Backend behavior:
- Default launch backend is `vllm-metal` (`vllm serve`).
- `mlx_lm.server` and `mlx-openai-server` are legacy fallback references only and are not part of the active runtime contract.

Source of truth contract:
- Runtime and gateway wiring are derived from registry state.
- Avoid ad-hoc edits to launch scripts for model assignment.

## Harmony / Parser Contract
For GPT-OSS entries, registry must keep:
- `tool_call_parser: harmony`
- `reasoning_parser: harmony`
- valid `chat_template`

For Qwen3 entries, registry must keep:
- `tool_call_parser: qwen3`
- `reasoning_parser: qwen3`
- optional discovered `chat_template`

`mlxctl verify` is expected to catch parser/template drift.

## Gateway Sync Contract
`mlxctl sync-gateway` updates:
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/config/env.local`

Current alias intent:
- `main` -> qwen3-next-80b (`8101`)
- `deep` -> gpt-oss-120b (`8100`)
- `fast` -> gpt-oss-20b (`8102`)
- `boost` / `boost-deep` -> Studio OptiLLM proxy (`4020`)

## Port Policy
- Team ports: `8100-8119`
- Experimental ports: `8120-8139`
- Active set currently uses only `8100/8101/8102`.

## Offload Policy
- Offload original artifacts only when `og_path` exists and differs from `cache_path`.
- Seagate offload remains backroom storage; only Studio/Mini-present models become active gateway handles.

## Notes
- Studio `/v1/models` may report snapshot-path IDs.
- Use registry + `mlxctl status` as canonical identity mapping.
- `mlxctl status --checks` reports runtime family and runtime model path for drift triage.
- `mlxctl mlx-launch-configure-vllm` rewrites `/opt/mlx-launch/bin/start.sh`
  to a registry-driven team-lane launcher for `vllm-metal`.
- Output-quality gate: run `platform/ops/scripts/mlx_quality_gate.py` after
  reboot/model changes to catch protocol leakage or hangs on `fast/main/deep`.
