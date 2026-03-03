# 2026-03-02 — websearch-orch Phase 2 closeout (round 5)

## Summary
Implemented a Phase 2 closeout tightening pass focused on grounded retrieval reliability and deterministic observability.

This round does not introduce Phase 3 synthesis/schema enforcement. It keeps Phase 2 retrieval behavior fail-open while adding clearer grounding telemetry and tighter default retrieval budgets.

## What changed
- `layer-tools/websearch-orch/app/main.py`
  - Tightened defaults:
    - `MIN_RESULT_CONTENT_CHARS=160`
    - `TRUST_DROP_BELOW_SCORE=0`
    - `RERANK_ENABLED=true`
    - `EXTERNAL_WEB_LOADER_MAX_URLS=10`
    - `EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS=2800`
    - `EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS=18000`
    - `EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS=700`
  - Added additive grounding gate payload:
    - `grounding_gate.status` (`pass|warn`)
    - `grounding_gate.grounded_sources`
    - `grounding_gate.min_required`
    - `grounding_gate.allowed_url_count`
  - Extended search log telemetry with grounding-gate fields:
    - `grounding_status`, `grounding_sources`, `grounding_required`, `grounding_allowed_urls`

- `layer-tools/websearch-orch/config/env.example`
  - Updated recommended defaults to match round-5 tightening profile.

- `layer-tools/websearch-orch/RUNBOOK.md`
  - Updated verification grep to include grounding-gate fields.
  - Updated recommended env block to round-5 defaults.

- `scripts/openwebui_phase_a_baseline.py`
  - Extended scoring output with `phase2_quality` metrics from `websearch-orch` logs:
    - `citation_map_ready_rate`
    - `grounding_warn_rate`
    - `placeholder_drop_events`
    - `unsupported_claim_count_total`
    - `budget_drop_events`
    - `dedupe_drop_events`
    - `domain_cap_drop_events`

- `docs/foundation/testing.md`
  - Added grounding-gate checks to Phase 2 tightening verification guidance.

- `NOW.md`
  - Set active work to websearch-orch Phase 2 closeout round 5.

- `BACKLOG.md`
  - Recorded round-5 implemented items and added grounding-gate exit criterion.

## Verification (FAST)
- `python3 -m py_compile layer-tools/websearch-orch/app/main.py scripts/openwebui_phase_a_baseline.py`
- `python3 scripts/openwebui_phase_a_baseline.py score --run-id PHASEA-001 --since "24 hours ago"`

## Notes
- `layer-tools/websearch-orch/CONSTRAINTS.md` is still absent; continued with least-risk interpretation per service guidance.
- Runtime service/env mutation on host (`/etc/homelab-llm/websearch-orch.env`) remains an operator step outside this repo commit.
