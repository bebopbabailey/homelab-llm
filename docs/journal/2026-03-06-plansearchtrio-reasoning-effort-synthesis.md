# 2026-03-06 — PlanSearchTrio deep-stage reasoning-effort wiring (canary)

## Goal
Apply `reasoning_effort=high` where it matters for trio quality (deep final synthesis/rewrite), keep early stages cheap, and preserve canary-only rollout.

## Changes
1. Trio plugin stage-scoped effort wiring
- Updated `layer-gateway/optillm-proxy/optillm/plugins/plansearchtrio_plugin.py`.
- Added deep-only stage logic:
  - `plansearchtrio_reasoning_effort_synthesis` (default `high`)
  - `plansearchtrio_reasoning_effort_rewrite` (default `high`)
- Effort is only attached when stage is `synthesis`/`rewrite` and model is the configured `deep` model.
- Added compatibility retry: if provider rejects `reasoning_effort`, retry once without it for that stage.

2. Unit-test coverage expansion
- Updated `layer-gateway/optillm-proxy/tests/test_plansearchtrio.py`.
- Added assertions for:
  - deep synthesis/rewrite includes `reasoning_effort=high`
  - non-synthesis stages do not include `reasoning_effort`
  - main-model fallback synthesis does not receive deep-only effort
  - rejection fallback retries without `reasoning_effort`

3. Service/runtime docs
- Updated `layer-gateway/optillm-proxy/SERVICE_SPEC.md` with new request-config keys and fallback behavior.
- Updated `layer-gateway/optillm-proxy/RUNBOOK.md` canary example and reasoning-effort note.
- Updated `docs/foundation/optillm-techniques.md` trio notes.
- Updated `docs/PLATFORM_DOSSIER.md` OptiLLM service inventory paragraph.

## Verification
FAST:
- `cd layer-gateway/optillm-proxy && uv run python -m unittest tests/test_plansearchtrio.py`
- Result: PASS (10 tests).

FULL:
- First canary run was invalid due auth missing (`401` across both baseline/candidate).
- Re-ran with key sourced from `../litellm-orch/config/env.local` and payload file:
  - Output: `/tmp/plansearchtrio_canary_reasoning_auth.json`
  - Gate: pass `true`
  - `empty_pass=true`, `error_text_pass=true`, `latency_pass=true`
  - `p95_ratio=0.9042` (`<= 1.75`)
  - Baseline (`boost-plan`) `p95=12.812`, `trunc=20`
  - Candidate (`boost-plan-trio`) `p95=11.5852`, `trunc=0`, `avg_chars=353.8`

## Decision
- Keep `boost-plan-trio` as canary.
- Deep final stages now intentionally trade latency budget for quality via high reasoning effort.
