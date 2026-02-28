# 2026-02-27 — websearch-orch Phase 2 tightening (round 4)

## Summary
Implemented a fourth tightening pass for `websearch-orch` focused on citation-grounding metadata and stricter retrieval quality controls.

Round 4 adds a citation contract block to `/search` responses, strengthens trust drop defaults, and increases duplicate/domain suppression signals so Phase 2 can be validated with deterministic log gates.

## What changed
- `layer-tools/websearch-orch/app/main.py`
  - Added env knobs:
    - `MAX_SOURCES_PER_DOMAIN`
    - `CITATION_CONTRACT_ENABLED`
    - `MIN_GROUNDED_SOURCES`
    - `SOURCE_TITLE_DEDUP_ENABLED`
  - Tightened defaults:
    - `MIN_RESULT_CONTENT_CHARS=120`
    - `TRUST_DROP_BELOW_SCORE=-1`
  - Added placeholder URL detection (`_is_placeholder_url`) and title-key normalization for dedupe.
  - Added title dedupe + per-domain source cap checks in `_keep_result`.
  - Updated trust policy flow:
    - drops placeholder URLs
    - assigns `orch_source_id` after final trust ordering
    - reports `placeholder_drops` in trust summary
  - Added `citation_contract` response payload:
    - `citation_map_status`
    - `citation_total`, `citation_mapped`, `citation_unmapped`
    - `allowed_urls`
    - per-source citation map (`source_id`, title, url, domain, trust_tier)
  - Added `quality_signals` response payload:
    - `dedupe_drops`, `domain_cap_drops`, `thin_content_drops`, `placeholder_drops`, `unsupported_claim_count`
  - Extended query log line with citation/quality counters.

- `layer-tools/websearch-orch/config/env.example`
  - Added new round-4 env keys and updated tightened defaults.

- `layer-tools/websearch-orch/RUNBOOK.md`
  - Added round-4 verification grep fields and recommended env values.

- `docs/foundation/testing.md`
  - Added citation-contract and quality-signal checks to Phase 2 tightening test steps.

- `NOW.md`
  - Updated active work to “Phase 2 tightening round 4”.

- `BACKLOG.md`
  - Recorded round-4 implemented items and added citation-contract exit criterion.

## Verification
- `python3 -m py_compile layer-tools/websearch-orch/app/main.py`
- Restart + health/search/log checks documented in runbook/testing.

## Notes
- `layer-tools/websearch-orch/CONSTRAINTS.md` is still missing; continued with least-risk interpretation.
- This round does not add new infrastructure. It tightens existing retrieval, trust, and observability behavior only.
