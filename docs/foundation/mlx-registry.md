# MLX Registry and Controller (Current)

## Purpose
Keep Studio MLX inference stable and repeatable with registry-driven model mapping,
Harmony-safe parser/template defaults for GPT-OSS, and deterministic LiteLLM alias wiring.

## Runtime Reality (2026-03-19)
- Active public Studio MLX inference listener:
  - `8101` -> `mlx-qwen3-next-80b-mxfp4-a3b-instruct` (`main`)
- Retired GPT rollback MLX slots:
  - `8100` (previous `deep` MLX rollback slot, now unloaded)
  - `8102` (previous `fast` MLX rollback slot, now unloaded)
- Canonical Mini -> Studio transport for active team lanes is the Studio LAN IP
  `192.168.1.72`; the MLX lane transport contract no longer depends on Studio
  Tailscale hostnames.
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
  "version": 2,
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
  },
  "lanes": {
    "8100": {
      "desired_target": {
        "target_slug": "mlx-gpt-oss-120b-mxfp4-q4",
        "repo_id": "mlx-community/gpt-oss-120b-MXFP4-Q4",
        "expected_served_model_identity": "mlx-gpt-oss-120b-mxfp4-q4"
      },
      "actual_serving_target": {
        "target_slug": "mlx-gpt-oss-120b-mxfp4-q4",
        "repo_id": "mlx-community/gpt-oss-120b-MXFP4-Q4",
        "expected_served_model_identity": "mlx-gpt-oss-120b-mxfp4-q4"
      },
      "last_known_good_target": {
        "target_slug": "mlx-gpt-oss-120b-mxfp4-q4",
        "repo_id": "mlx-community/gpt-oss-120b-MXFP4-Q4",
        "expected_served_model_identity": "mlx-gpt-oss-120b-mxfp4-q4"
      },
      "actual_served_model_identity": "mlx-gpt-oss-120b-mxfp4-q4",
      "health_state": "serving",
      "reconciliation_state": "converged",
      "last_failure": {},
      "last_transition_time": "2026-03-13T00:00:00Z"
    }
  }
}
```

Key fields:
- `model_id`: canonical handle identity.
- `cache_path`: runtime artifact path.
- `source_path`: canonical source path (usually same as `cache_path`).
- `port`: compatibility mirror of actual serving truth for the current model.
- `chat_template` / `tool_call_parser` / `reasoning_parser`: parser safety contract.
- `chat_template_args`: logical GPT/chat-template kwargs. Under `vllm-metal`,
  `mlxctl` compiles these into `--default-chat-template-kwargs`; under
  `mlx_lm.server`, it compiles them into `--chat-template-args`.
- `og_path` (optional): original artifact path used for conversion/offload workflows.
- `lanes.<port>.desired_target`: operator intent.
- `lanes.<port>.actual_serving_target`: last target that actually proved ready.
- `lanes.<port>.last_known_good_target`: explicit rollback reference.
- `lanes.<port>.actual_served_model_identity`: observed `/v1/models` identity.
- `lanes.<port>.health_state` / `reconciliation_state`: control-plane truth for serving vs transition vs failure.

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
- Runtime and gateway wiring are derived from registry state, but desired state and actual serving state are independent lane fields.
- Avoid ad-hoc edits to launch scripts for model assignment.
- Mutating commands are parity-gated against the Studio binary.
  Run `mlxctl studio-cli-sha` and, when needed, `mlxctl sync-studio-cli`.
- `mlxctl reconcile` is dry-run by default; mutation requires `--apply`.
  Stale assignment candidates are only entries with no listener, no runtime
  process, and no successful local `/v1/models` probe.
- `load` now updates `desired_target` immediately, but only updates
  `actual_serving_target` after preflight and full readiness pass.
- Failed loads never claim serving success; state remains explicit when desired
  differs from actual or when a lane is down.

## Harmony / Parser Contract
For GPT-OSS entries, registry must keep:
- `tool_call_parser: harmony`
- `reasoning_parser: harmony`
- valid `chat_template`
- `chat_template_args` aligned with the GPT lane policy (currently
  `{"enable_thinking": false, "reasoning_effort": "low"}`)

For Qwen3-Next entries on the main lane, registry must keep:
- `vllm.profile: qwen3-next-80b`
- `vllm.tool_choice_mode: auto`
- `vllm.tool_call_parser: hermes`
- no default reasoning parser

For `vllm-metal` launch behavior, registry now supports a nested `vllm` block:
- `vllm.profile` (resolved against required metadata in `platform/ops/mlx-runtime-profiles.json`)
- `vllm.tool_choice_mode` (`none|auto`)
- `vllm.tool_call_parser`, `vllm.reasoning_parser`
- `vllm.max_model_len`, `vllm.memory_fraction`, `vllm.async_scheduling`

Runtime-profile metadata is required:
- file: `platform/ops/mlx-runtime-profiles.json`
- schema versioned
- `vllm-render --validate` fails if profile resolution is missing or ambiguous
- family defaults now live in metadata instead of scattered conditionals

Runtime compatibility is resolved at launch time:
- Registry keeps logical family/profile defaults and lets `mlxctl` resolve the
  effective runtime parser enums from current vLLM capabilities.
- Lane-local `vllm` overrides may intentionally diverge from top-level family
  metadata when a specific runtime needs a different parser contract.
- `tool_choice_mode=auto` is fail-closed: launch is blocked if the current vLLM
  binary lacks `--enable-auto-tool-choice` or a compatible tool parser.
- Family/runtime preflight runs before a healthy lane is torn down:
  - architecture/config preflight in the serving venv
  - family/parser profile validation
  - runtime capability validation
- Readiness is no longer pid/port based. vLLM-backed loads require:
  - service exists / not disabled
  - stable process
  - successful `/v1/models` identity check
  - successful minimal non-streaming `/v1/chat/completions` probe
  - two consecutive full passes with no restart between them

Current staged default:
- `main` (`8101`, qwen3-next-80b) uses `tool_choice_mode=auto`.
- Active `8101` lock render uses `vllm.profile=qwen3-next-80b`,
  `vllm.tool_call_parser=hermes`, and `vllm.reasoning_parser=null`.
- `deep`/`fast` remain on `tool_choice_mode=none` until explicitly changed.
- GPT-OSS family defaults now carry chat-template kwargs into the vLLM render so
  direct canaries and future lane reloads do not silently drop the GPT thinking
  controls on the active `vllm-metal` path.
- Team lanes render `VLLM_METAL_MEMORY_FRACTION=auto`.
- Team lanes render `--host 192.168.1.72` for the active Mini -> Studio path.
- Team lanes do not require backend bearer auth.
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
- public GPT aliases `fast` and `deep` are no longer backed by MLX team lanes;
  they now route to shared `llmster` on `8126`

## Port Policy
- Team ports: `8100-8119`
- Experimental ports: `8120-8139`
- Active public MLX set currently uses only `8101`.
- Conservative lane defaults when registry fields are missing:
  - `8100` (`gpt-oss-120b`): `vllm_max_model_len=65536`, `vllm_memory_fraction=0.55`, `vllm_async_scheduling=false`
  - `8101` (`llama-3.3-70b`): `vllm_max_model_len=65536`, `vllm_memory_fraction=auto`, `vllm_async_scheduling=false`
  - `8102` (`gpt-oss-20b`): `vllm_max_model_len=32768`, `vllm_memory_fraction=0.45`, `vllm_async_scheduling=false`

## Offload Policy
- Offload original artifacts only when `og_path` exists and differs from `cache_path`.
- Seagate offload remains backroom storage; only Studio/Mini-present models become active gateway handles.

## Notes
- Studio `/v1/models` may report snapshot-path IDs.
- Use registry lane state + `mlxctl status` as canonical control-plane truth.
- `mlxctl status --json` is JSON-only; add `--table` for mixed human+JSON output.
- `status=running` can be valid even when `listener_visible=false` (process is
  present; listener visibility may be delayed or restricted).
- `mlxctl status --checks` reports runtime family and runtime model path for drift triage.
- For team lanes, `status --checks` also reports `launchd_label`,
  `launchd_loaded`, `launchd_disabled`, and `http_models_ok`.
- `http_models_ok=true` is the serving-truth signal when listener visibility is
  delayed or hidden under root-owned launchd process ownership.
- For vLLM readiness and successful load transitions, `/v1/chat/completions`
  is the primary serving proof and `/v1/models` is an identity check only.
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
- For `main` tool-calling work, the acceptance bar is structured `tool_calls`
  from `8101`, not just HTTP 200 or plain-text tool markup.
