# Runtime Lock

This document and `platform/ops/runtime-lock.json` define the current locked runtime
contract for the active LiteLLM + OptiLLM + vLLM-metal stack.

Compatibility-first note:
- Runtime lock v2 adds `service_refs` and path refs such as
  `litellm.router_config_ref` so runtime validation can resolve canonical
  service IDs while the filesystem still uses `layer-*` paths.
- Raw path fallback fields have been removed from the lock schema; repo-local
  validators and tooling should resolve canonical service paths through
  `platform/registry/services.jsonl`.

## Purpose
- Make runtime assumptions explicit and reviewable.
- Prevent drift between repo state, Studio runtime, and gateway behavior.
- Give coding agents a single place to verify what is live and intentionally locked.
- Keep repo-local ops tooling path-agnostic so later `services/` path moves do
  not require another runtime-lock schema break.

## Current canon
- `layer-gateway/optillm-proxy` deploys by exact git SHA to Studio.
- `optillm` is pinned to `0.3.12` from PyPI, not a git source.
- Deploy-time patching is not allowed.
- LiteLLM binds `0.0.0.0:4000`; canonical infra URL is `http://192.168.1.71:4000/v1`.
- Studio OptiLLM binds `192.168.1.72:4020` and points upstream at `http://192.168.1.71:4000/v1`.
- LiteLLM keeps `drop_params: true`.
- LiteLLM fallbacks include `fast -> main`.
- LiteLLM no longer owns canonical GPT response formatting for `main`, `fast`,
  or `deep`; it keeps only a narrow request-default shim that injects
  `reasoning_effort=low` when omitted for `fast`, `deep`, and internal worker
  alias `code-reasoning`.
- The remaining active public MLX lane `8101` renders `VLLM_METAL_MEMORY_FRACTION=auto`.
- The remaining active public MLX lane `8101` renders `--host 192.168.1.72`.
- The remaining active public MLX lane does not use backend bearer auth.
- The remaining active public MLX lane keeps `--no-async-scheduling`.
- Lane `8101` is the locked Qwen3-Next main lane:
  `--enable-auto-tool-choice`, `--tool-call-parser hermes`, and no
  `--reasoning-parser`. `tool_choice="required"` and named forced-tool
  semantics remain unsupported on the current `vllm-metal` build and are not
  promotion blockers for public `main`.
- Paged attention remains off.

## OpenCode lane policy
- OpenCode repo default lane is `deep`.
- `main` is the direct-lane canary on Qwen3-Next and is validated for
  non-stream `tool_choice=auto`, long-context sanity, and branch-style
  concurrency.
- The repo-standard noop `tool_choice=auto` probe must pass natively on direct
  `8101`.
- The stricter single-tool argument-bearing `tool_choice=auto` probe must pass
  natively on direct `8101`.
- Structured outputs are outside the accepted public `main` contract on the
  current runtime because both of the current non-stream direct `8101` paths
  are failing on the present backend path:
  - exact documented OpenAI-compatible `response_format.json_schema`
  - exact vLLM-native `structured_outputs.json`
  LiteLLM reproduces the same failure text rather than introducing a separate
  gateway-only error mode. This is a known accepted limitation, not an active
  closeout blocker for `main`.
- `fast` is boxed in as a synthesis-only lane in repo-local OpenCode config.
- `fast` is currently live on Studio `8126` through `llmster` and is part of
  the canonical shared GPT runtime stack on `8126`.
- Public GPT lanes are Chat Completions-first in the current hardening phase.
- `/v1/responses` remains in validation scope for GPT lanes, but it is advisory
  unless a defect there also affects the public Chat Completions lane.
- No temporary GPT rollout aliases are part of the active gateway contract.
- Historical note: a temporary non-public canary alias was used before
  canonical public `deep` was repointed.
- OptiLLM planning aliases and OpenHands Phase B aliases are not part of the
  current active gateway contract.

## Approved lane targets and retired shadow space
- `main` target backend: `Qwen3-Next-80B-A3B-Instruct` on `vllm-metal`.
- `main` explicit fallback backend remains the same Qwen family on
  `mlx-openai-server`, but only as dormant recovery metadata rather than active
  project work.
- `main` is accepted for public use on the basis of non-stream auto tool use,
  long-context sanity, branch-generation suitability, and
  concurrency/throughput posture.
- `main-mtp-shadow` remains later optimization only and is not part of the
  boring baseline.
- legacy `main` shadow/fallback rollout space on `8123/8124/8125` is retired
  and no longer approved as rollout or recovery space.
- `fast` and `deep` target backend family: `llmster`-backed llama.cpp behind the
  repo-owned `layer-inference/llama-cpp-server` boundary.
- Canonical GPT artifacts for `fast` and `deep` are MXFP4 GGUF variants:
  `llmster-gpt-oss-20b-mxfp4-gguf` and `llmster-gpt-oss-120b-mxfp4-gguf`.
- Direct truth-path validation for GPT lanes stays on raw `llama-server`
  mirrors, while the public client path stays LiteLLM -> `llmster`. Raw
  divergence alone does not block promotion unless it exposes a crash, gross
  corruption, or a reproducible bug that also appears on direct `llmster` or
  public LiteLLM.
- Studio GPT retention policy is `active runtime models + one staged next
  artifact`; stale weights are pruned before GPT lane cutovers.
- Canonical GPT lane invariants:
  - explicit `lms load` residency
  - JIT loading disabled
  - auto-evict disabled
  - no TTL-based auto-unload for canonical lanes
  - no repetition penalties for GPT-OSS
  - raw standalone launchers use `--jinja`
- The GPT migration path is complete on shared `8126`.
- Shared `8126` was accepted only after both:
  - preflight `lms load --estimate-only`
  - actual post-load shared-posture proof after both models were loaded and idle
- Actual post-load shared-posture proof required:
  - intended loaded set visible in `lms ps --json`
  - intended loaded set visible in `/v1/models`
  - actual memory-state capture after dual-load quiescence
  - a second idle memory-state capture after a 5-minute wait
  - a `fast` regression rerun under the actual shared loaded posture
- `deep` usable-success acceptance gate is:
  - plain chat clean
  - structured simple clean
  - structured nested clean
  - auto noop strong
  - auto arg-bearing usable at `>= 8/10` on direct `llmster` and public LiteLLM
  - at least one constrained mode strong:
    - `tool_choice="required" >= 9/10`, or
    - named-tool forcing `>= 9/10`
  - crashes, listener loss, sustained readiness regressions, repeated `5xx`,
    and repeated timeouts remain blockers
- Current locked `deep` result on the shared `8126` posture:
  - public `deep` plain chat `5/5`
  - public `deep` structured simple `5/5`
  - public `deep` structured nested `5/5`
  - public `deep` auto noop `10/10`
  - public `deep` auto arg-bearing `10/10`
  - public `deep` required arg-bearing `9/10`
  - named forced-tool choice is unsupported on the current backend path and
    returns backend-visible `400` errors for object-form `tool_choice`
- The codified public `deep` contract is therefore:
  - Chat Completions-first
  - `auto` strong enough for ordinary use
  - `required` strong and accepted as the constrained-mode success path
  - named forced-tool choice unsupported and non-blocking on the current GPT
    backend family
- Internal worker alias `code-reasoning` is not a public lane and inherits the
  current `deep` backend and formatting contract.
- `8126` is the only active canonical GPT listener in the `812x` range.
- `8123/8124/8125` are retired shadow ports and are no longer approved rollout
  targets.

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
- service refs and exact runtime file paths resolved from the monorepo tree
- OptiLLM package provenance or version
- Studio OptiLLM deploy contract
- LiteLLM resilience settings (`drop_params`, fallbacks)
- MLX lane auth, memory-fraction policy, async baseline, paged-attention state,
  or any locked lane-local parser override
- approved shadow retirement labels, ports, or backend-family decisions

## Intentionally deferred
- Pushcut reintegration in LiteLLM main runtime
- paged-attention evaluation
- async-scheduler re-enable for vLLM-metal lanes
