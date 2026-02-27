# 2026-02-27 — Runtime doc hardening for `vllm-metal` canonical reality

## Summary
Performed a scoped consistency hardening pass across repo-root docs,
`docs/foundation`, `layer-gateway/litellm-orch`, and `layer-inference` to
remove stale runtime claims and reduce agent confusion.

## What changed
- Updated active docs that still described `mlx_lm.server` as current runtime to
  reflect the active `vllm-metal` (`vllm serve`) contract.
- Corrected stale streaming guidance in integration docs to match current
  pass-through default (`stream` can still be overridden per call).
- Added explicit historical framing in `layer-gateway/litellm-orch/decision-log.md`.
- Archived stale long-form notes and replaced active files with canonical stubs:
  - `layer-gateway/litellm-orch/TODO.md` -> archived snapshot
    `docs/archive/2026-02-layer-gateway-litellm-orch-TODO.md`
  - `layer-inference/docs/ENSEMBLE_PARAMETER_SUPPORT.md` -> archived snapshot
    `docs/archive/2026-02-layer-inference-ensemble-parameter-support.md`
- Updated `layer-inference/optillm-local` docs to separate active
  `vllm-metal` tuning/probe workflows from retained legacy `mlx-lm` research.

## Rationale
The active runtime contract for Studio team lanes is now `vllm-metal` under
`mlxctl`/launchd management. Leaving legacy-runtime wording in active docs caused
drift and repeatedly confused agent planning/execution.

## Follow-up
- Keep historical details in `docs/archive/*` and journal entries.
- Keep active files focused on current runtime behavior and operator actions.
