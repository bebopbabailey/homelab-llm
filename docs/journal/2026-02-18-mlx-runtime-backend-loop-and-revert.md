# 2026-02-18 — MLX runtime backend loop and revert (Omni/llama.cpp -> per-port mlx-openai-server)

## Goal / question
Determine the most durable backend path for GPT-OSS + Qwen serving with stable parsing,
quality, and low operational friction for LiteLLM aliases and OptiLLM boost lanes.

## Timeline summary
- Started from `mlx-openai-server` per-port operation.
- Evaluated `mlx-omni-server` as a feature-forward consolidation path.
- Evaluated `llama.cpp` as a potential robustness fallback for GPT-family Harmony handling.
- Reverted to per-port `mlx-openai-server` as the active runtime contract.

## Why the revert
- Existing per-port MLX lane setup was the most stable in current homelab operation.
- GPT-OSS parser/template behavior was already known and operationally controllable with
  registry + parser/template fields.
- `llama.cpp` exploration was useful, but migration cost + behavior differences were not
  justified for immediate production path.
- Team preference prioritized quality/reliability over backend novelty.

## Current runtime contract (post-revert)
- Studio active MLX listeners:
  - `8100` -> `mlx-gpt-oss-120b-mxfp4-q4` (deep)
  - `8101` -> `mlx-qwen3-next-80b-mxfp4-a3b-instruct` (main)
  - `8102` -> `mlx-gpt-oss-20b-mxfp4-q4` (fast)
- Runtime command family observed: `mlx-openai-server launch`.
- LiteLLM aliases map to these lanes; `boost`/`boost-deep` remain OptiLLM-routed.

## Risks / follow-up
- Keep Harmony parser/template verification strict in `mlxctl verify` for GPT-OSS entries.
- Avoid backend churn without a migration checklist + rollback path.
- Re-test Omni/llama.cpp only when a specific blocker exists and acceptance criteria are defined in advance.
