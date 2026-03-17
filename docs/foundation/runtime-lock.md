# Runtime Lock

This document and `platform/ops/runtime-lock.json` define the current locked runtime
contract for the active LiteLLM + OptiLLM + vLLM-metal stack.

## Purpose
- Make runtime assumptions explicit and reviewable.
- Prevent drift between repo state, Studio runtime, and gateway behavior.
- Give coding agents a single place to verify what is live and intentionally locked.

## Current canon
- `layer-gateway/optillm-proxy` deploys by exact git SHA to Studio.
- `optillm` is pinned to `0.3.12` from PyPI, not a git source.
- Deploy-time patching is not allowed.
- LiteLLM binds `0.0.0.0:4000`; canonical infra URL is `http://192.168.1.71:4000/v1`.
- Studio OptiLLM binds `192.168.1.72:4020` and points upstream at `http://192.168.1.71:4000/v1`.
- LiteLLM keeps `drop_params: true`.
- LiteLLM fallbacks include `fast -> main`.
- Active MLX lanes `8100/8101/8102` render `VLLM_METAL_MEMORY_FRACTION=auto`.
- Active MLX lanes `8100/8101/8102` render `--host 192.168.1.72`.
- Active MLX lanes do not use backend bearer auth.
- Active MLX lanes keep `--no-async-scheduling`.
- Lane `8101` is the locked tool-capable Llama 3.3 lane:
  `--enable-auto-tool-choice`, `--tool-call-parser llama3_json`, and no
  `--reasoning-parser`.
- Paged attention remains off.

## OpenCode lane policy
- OpenCode repo default lane is `deep`.
- `main` is the direct-lane canary on Llama 3.3 and is the repo's validated
  tool-capable lane.
- `fast` is boxed in as a synthesis-only lane in repo-local OpenCode config.
- GPT-OSS `fast` tool-calling is not part of the locked runtime contract until a
  direct `vllm-metal` canary proves structured tool calls reliably.
- OptiLLM planning aliases are not part of the repo-local OpenCode hardening
  baseline.

## Validation modes
- FAST:
  - local repo and config checks only
  - safe for CI
- FULL:
  - FAST checks plus Studio and Mini runtime verification
  - validates launchd/plist/runtime package state
  - validates the locked `8101` Llama tool-calling render from launchd argv

## Update rules
Update both the doc and `platform/ops/runtime-lock.json` if any of these change:
- locked submodule SHAs
- OptiLLM package provenance or version
- Studio OptiLLM deploy contract
- LiteLLM resilience settings (`drop_params`, fallbacks)
- MLX lane auth, memory-fraction policy, async baseline, paged-attention state,
  or any locked lane-local parser override

## Intentionally deferred
- Pushcut reintegration in LiteLLM main runtime
- paged-attention evaluation
- async-scheduler re-enable for vLLM-metal lanes
