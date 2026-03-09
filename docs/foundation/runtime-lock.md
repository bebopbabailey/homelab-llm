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
- LiteLLM keeps `drop_params: true`.
- LiteLLM fallbacks include `fast -> main`.
- Active MLX lanes `8100/8101/8102` render `VLLM_METAL_MEMORY_FRACTION=auto`.
- Active MLX lanes require `--api-key`.
- Active MLX lanes keep `--no-async-scheduling`.
- Paged attention remains off.

## Validation modes
- FAST:
  - local repo and config checks only
  - safe for CI
- FULL:
  - FAST checks plus Studio and Mini runtime verification
  - validates launchd/plist/runtime package state

## Update rules
Update both the doc and `platform/ops/runtime-lock.json` if any of these change:
- locked submodule SHAs
- OptiLLM package provenance or version
- Studio OptiLLM deploy contract
- LiteLLM resilience settings (`drop_params`, fallbacks)
- MLX lane auth, memory-fraction policy, async baseline, or paged-attention state

## Intentionally deferred
- Pushcut reintegration in LiteLLM main runtime
- paged-attention evaluation
- async-scheduler re-enable for vLLM-metal lanes
