# 2026-03-03 — OptiLLM coding-quality profiles on vLLM-metal

## Why
The primary objective shifted to coding-agent quality for deep planning and
system introspection, while staying on the canonical Studio `vllm-metal`
backend and preserving LiteLLM-first client routing.

## What changed
1. Deterministic OptiLLM coding aliases (LiteLLM)
- Added curated aliases in `layer-gateway/litellm-orch/config/router.yaml`:
  - `boost-plan` -> `plansearch-openai/deep`
  - `boost-plan-verify` -> `self_consistency-openai/deep`
  - `boost-ideate` -> `moa-openai/deep`
  - `boost-fastdraft` -> `bon-openai/fast`
- Kept existing `boost` and `boost-deep` request-body behavior unchanged.

2. Harmony normalization coverage
- Extended GPT-lane harmony guardrail target list to include new `boost-*`
  aliases so normalization behavior remains consistent.

3. OpenCode ergonomics
- Updated bootstrap defaults to:
  - `model=litellm/boost-plan`
  - `small_model=litellm/boost-fastdraft`
- Added new models to generated OpenCode provider model list.

4. Documentation canon updates
- Updated `docs/INTEGRATIONS.md`, `docs/OPENCODE.md`,
  `docs/foundation/optillm-techniques.md`,
  `layer-gateway/optillm-proxy/SERVICE_SPEC.md`, and
  `layer-gateway/litellm-orch/README.md`.
- Clarified that deterministic model-prefix selection is used to avoid
  request-body coupling for OpenCode profile routing.

## Scope and constraints
- No new ports, no host/bind changes, no new direct client exposure.
- Studio OptiLLM remains `0.0.0.0:4020` with auth and LiteLLM-first client path.
- Team MLX lanes remain `mlxctl`-managed and unchanged.

## Verification notes (FAST)
- Router config includes all new aliases and harmony targets.
- OpenCode bootstrap script passes shell syntax check.
- Alias references are present across gateway/foundation/root docs.

## Next
- Run canary comparison on representative coding tasks:
  `main` vs `boost-plan` + `boost-plan-verify`.
- Capture token-efficiency and quality deltas before widening defaults.
