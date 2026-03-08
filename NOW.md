# NOW

Active
- Web search supported-path reset (active):
  - Delete LiteLLM web-search schema middleware and legacy canary-alias residue.
  - Remove `websearch-orch` from repo and live Mini deployment.
  - Cut Open WebUI over to native SearXNG + `safe_web` with explicit documented env controls.
  - Refresh canonical docs, runbooks, and end-to-end validation on the supported path.
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
- Run supported-path validation sweep for Open WebUI web search, then resume the 50-prompt blind A/B scoring pass.
