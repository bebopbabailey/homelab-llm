# NOW

Active
- Transcribe helper restoration (active):
  - Restore `config/transcribe_utils.py` as the shared cleanup helper surface.
  - Rebind `transcribe_guardrail.py` to shared helpers instead of copied local logic.
  - Recover `tests/test_transcribe_baseline.py` and lock wrapper/punctuation semantics.
- PlanSearchTrio forensic handoff audit (active):
  - Build implementation-only file inventory with stage timeline and risk surface map for associate review.
- Vector DB docs-only quality gate hardening (active):
  - Add auto-judge + triage workflow to avoid full manual grading.
  - Shift score/gates to answerability-aware metrics before locking defaults.
  - Calibrate docs signal matching (`exact_lookup=all`, non-exact=`min_k=2`).
  - Keep `bad_hit_rate_at_5` diagnostic-only while hard-gating on core IR + negative FP.
  - Run docs corpus gate with <=5 minute manual review budget.
- PlanSearchTrio blind quality-gate tooling (active):
  - Add reproducible A/B capture + blind-packet + scorer scripts.
  - Wire canonical runbook/testing docs for 50-prompt human rubric gate.
  - Add grading accelerator sheet (`ab_grade_assist.py`) and numeric CLI (`ab_quick_grade.py`) for faster human review.
  - Soft-promote OpenCode default to `boost-plan-trio` with explicit fallback to `boost-plan`.

NEXT UP
- Resume the 50-prompt blind A/B scoring pass and vector DB docs-only quality gate work.
