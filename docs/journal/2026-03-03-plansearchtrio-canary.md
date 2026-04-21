# 2026-03-03 — PlanSearchTrio canary wiring (OptiLLM + LiteLLM)

## Why
Stock `plansearch` runs internal attempts serially and previously used a hidden
server-global `n` in `execute_single_approach`, which makes request behavior
harder to reason about. We need an explicit canary path for staged
fast/main/deep orchestration while preserving one-call client ergonomics.

## What changed
1. Added a new OptiLLM plugin approach: `plansearchtrio`
- File: `layer-gateway/optillm-proxy/optillm/plugins/plansearchtrio_plugin.py`
- Implements staged flow:
  - triage (fast)
  - parallel candidate generation (fast + main)
  - critique/prune (main)
  - synthesis (deep)
  - verifier + bounded repair loop (fast/main/deep)
- Supports request-level knobs via `request_config`:
  - candidate counts, keep count, max workers, repair rounds
  - per-stage token budgets
  - optional per-stage model overrides
  - stage budget defaults are bounded by request token cap (`max_completion_tokens`
    / `max_tokens`) for latency safety

2. Added unit tests for plugin behavior
- File: `layer-gateway/optillm-proxy/tests/test_plansearchtrio.py`
- Covers parameter clamping/model selection and bounded repair-loop execution.

3. Patched stock `plansearch` request-`n` semantics in local patchset
- File: `layer-gateway/optillm-proxy/patches/optillm.patch`
- `execute_single_approach(... plansearch ...)` now pins internal `plansearch`
  to `n=1` per outer pipeline run, so final output count is governed only by
  outer request `n` handling.

4. Added deterministic canary alias in LiteLLM
- File: `layer-gateway/litellm-orch/config/router.yaml`
- Added:
  - `boost-plan-trio` -> `plansearchtrio-deep`
- Extended harmony guardrail target models to include `boost-plan-trio`.

5. Updated runtime docs
- `layer-gateway/optillm-proxy/SERVICE_SPEC.md`
- `layer-gateway/optillm-proxy/RUNBOOK.md`
- `layer-gateway/optillm-proxy/README.md`
- `docs/foundation/optillm-techniques.md`
- `docs/INTEGRATIONS.md`
- `docs/OPENCODE.md`
- `NOW.md`

6. Added OpenCode bootstrap alias parity
- File: `platform/ops/scripts/setup-opencode.sh`
- Added `boost-plan-trio` to generated provider model list.

## Scope guardrails
- No new ports/binds/LAN exposure.
- No dependency or lockfile changes.
- Existing `boost-plan` path remains unchanged; trio is canary-only.

## FAST verification
- `uv run python -m unittest tests/test_router_meta.py tests/test_plansearchtrio.py`
- `uv run python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('../litellm-orch/config/router.yaml').read_text())"`
- `rg -n "boost-plan-trio|plansearchtrio" layer-gateway/litellm-orch/config/router.yaml docs layer-gateway/optillm-proxy`

## Next
- Run side-by-side quality/latency eval for coding tasks:
  `boost-plan` vs `boost-plan-trio`.
- If stable and better, decide whether to promote trio as OpenCode default.

## Canary results (20x2)
- Harness: 20 prompts each for `boost-plan` and `boost-plan-trio`
  (`max_tokens=160`).
- `boost-plan`: 20/20 responses returned; 20/20 included truncation text;
  latency p50 ~9.68s, p95 ~9.83s.
- `boost-plan-trio`: 20/20 responses returned; 0/20 truncation text;
  latency p50 ~14.12s, p95 ~14.85s.
- Quality gate failure: multiple `boost-plan-trio` outputs returned empty
  `message.content`.

## Decision
- `boost-plan-trio` remains canary-only.
- Do not promote trio to default OpenCode plan alias until empty-output defects
  are fixed and a repeat canary passes.

## Stabilization pass (implementation)
- Hardened `plansearchtrio` response extraction to handle structured message
  content payloads (string/list/object variants).
- Added bounded stage retries and optional synthesis fallback model path when
  deep-stage synthesis returns empty output.
- Added deterministic candidate ordering for parallel candidate generation
  before `k_keep` selection.
- Added explicit error outputs (`PLANSEARCHTRIO_ERROR:*`) instead of silent
  empty final content when all retries/fallbacks fail.
- Added canary harness:
  `layer-gateway/optillm-proxy/scripts/canary_plansearch_profiles.py`
  with prompt fixture
  `layer-gateway/optillm-proxy/scripts/canary_prompts_plansearch.txt`.
- Promotion gate now codified in tooling:
  - candidate empty outputs = `0`
  - candidate p95 latency `<= 1.75x` baseline (`boost-plan`)

## Live canary rerun (2026-03-04)
- Deployed `optillm-proxy` commit `b0aed9e` to Studio via
  `layer-gateway/optillm-proxy/scripts/deploy_studio.sh`.
- Smoke behavior:
  - non-stream trio call returned explicit error text
    (`PLANSEARCHTRIO_ERROR: no non-empty candidates generated after retries`)
    rather than silent empty output.
  - stream SSE remained functional (`stream_sse_seen=yes`).
- Full 20x2 canary executed with:
  `./scripts/canary_plansearch_profiles.py --model-a boost-plan --model-b boost-plan-trio --max-tokens 160`.

Result summary:
- Baseline (`boost-plan`):
  - `ok=20/20`, `empty=0`, `trunc=20`
  - `p50=9.6449s`, `p95=9.8435s`
- Candidate (`boost-plan-trio`):
  - `ok=20/20`, `empty=0`, `trunc=0`
  - `p50=24.0223s`, `p95=28.4884s`
- Gate outcome:
  - `empty_pass=true`
  - `latency_pass=false` (`p95_ratio=2.8941`, threshold `1.75`)
  - overall `pass=false`

Decision:
- `boost-plan-trio` remains canary-only.
- Next work should focus on latency reduction before any promotion plan.

## Compact-mode canary rerun (2026-03-05)
- Deployed `optillm-proxy` commit `5aed822` to Studio via
  `layer-gateway/optillm-proxy/scripts/deploy_studio.sh`.
- Implemented compact/auto trio defaults, latency-budget stage skipping, and
  auto-fallback responses (no `PLANSEARCHTRIO_ERROR` marker in canary outputs).
- Full 20x2 canary executed with compact overrides:
  `./scripts/canary_plansearch_profiles.py --model-a boost-plan --model-b boost-plan-trio --model-b-extra-json '{"plansearchtrio_mode":"auto","plansearchtrio_latency_budget_ms":17000}' --max-tokens 160`.

Result summary:
- Baseline (`boost-plan`):
  - `ok=20/20`, `empty=0`, `error_text=0`, `trunc=20`
  - `p50=10.9666s`, `p95=19.7371s`
- Candidate (`boost-plan-trio`, compact):
  - `ok=20/20`, `empty=0`, `error_text=0`, `trunc=0`
  - `p50=12.1506s`, `p95=24.4424s`
- Gate outcome:
  - `empty_pass=true`
  - `error_text_pass=true`
  - `latency_pass=true` (`p95_ratio=1.2384`, threshold `1.75`)
  - overall `pass=true`

Decision:
- Trio compact path now meets the canary gate.
- Keep alias in canary designation until a promotion-policy decision is
  recorded (default route vs selective use for coding-plan workloads).
