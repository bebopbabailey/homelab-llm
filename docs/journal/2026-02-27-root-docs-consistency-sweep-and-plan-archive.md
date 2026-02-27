# 2026-02-27 — Root docs consistency sweep + `implementation_plan.md` archive

## Goal
Run a root-doc consistency correction pass after stale alias and diagnostics
drift were identified, and archive obsolete root planning material.

## What changed
- Updated root alias guidance:
  - `README.md`: removed active `swap` / `x1..x4` language.
  - `BACKLOG.md`: replaced stale alias mapping task with current policy wording.
- Updated diagnostics auth example:
  - `DIAGNOSTICS.md`: readiness check now uses `LITELLM_MASTER_KEY`.
- Removed non-repo citation artifacts:
  - `CREDENTIALS.md`: removed `turn...` citation markers.
  - `OPTILLM_MLX_BACKEND_PATCH.md`: removed `turn...` citation markers.
- Archived obsolete root implementation plan:
  - moved `implementation_plan.md` -> `docs/archive/implementation_plan.md`.

## Why
- `swap*` aliases were previously deprecated for active use in favor of
  temporary `metal-test-*` experiment labels; root docs still contained stale
  alias wording.
- Root diagnostics used an inconsistent key variable name in examples.
- Artifact citation markers were not valid repository-local references.
- Keeping `implementation_plan.md` at repo root caused noise after completion.

## Validation
```bash
rg -n "\bswap\b|x1|x2|x3|x4" README.md BACKLOG.md
rg -n "LITELLM_API_KEY|LITELLM_MASTER_KEY" DIAGNOSTICS.md
rg -n "cite|turn[0-9]+search|turn[0-9]+view" CREDENTIALS.md OPTILLM_MLX_BACKEND_PATCH.md
test -f docs/archive/implementation_plan.md && test ! -f implementation_plan.md
```

## Outcome
- Status: PASS (FAST)
- Root docs now align with current policy and remove stale guidance for this
  sweep scope.
