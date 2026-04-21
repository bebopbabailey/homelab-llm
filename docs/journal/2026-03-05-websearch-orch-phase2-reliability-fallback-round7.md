# 2026-03-05 — websearch-orch Phase 2 reliability fallback (round 7)

## Summary
- Implemented deterministic SearX fallback attempts in `websearch-orch` for
  empty-result bursts.
- Added additive fetch diagnostics to `/search` responses and extended search
  log telemetry for fallback attribution.
- Extended canonical scorer telemetry with fallback metrics.
- Phase 2 closeout remains active: `PHASE2-EXIT-007` passed; `PHASE2-EXIT-008`
  failed grounding/citation gates.

## Files changed
- `layer-tools/websearch-orch/app/main.py`
- `layer-tools/websearch-orch/config/env.example`
- `layer-tools/websearch-orch/RUNBOOK.md`
- `scripts/openwebui_phase_a_baseline.py`
- `docs/foundation/testing.md`
- `NOW.md`
- `BACKLOG.md`

## Implementation details
- Added fallback env knobs:
  - `SEARX_FALLBACK_ENABLED`
  - `SEARX_FALLBACK_MAX_ATTEMPTS`
  - `SEARX_FALLBACK_BACKOFF_MS`
  - `SEARX_FALLBACK_BROADEN_DROP_YEAR`
- Added query attempt chain with dedupe:
  - `guarded_primary`
  - `guarded_no_language`
  - `parsed_no_language`
  - optional `*_drop_year` broadened attempts
- Added `/search` response field:
  - `fetch_diagnostics` (attempt list, selected attempt, fallback usage)
- Added search log fields:
  - `fetch_attempts`
  - `fallback_used`
  - `fetch_selected`
  - `fetch_empty_attempts`
  - `fetch_error_attempts`
- Added scorer metrics:
  - `fallback_used_events`
  - `fallback_success_events`
  - `fallback_empty_events`
  - `fetch_error_attempt_events`

## Verification
- Compile:
  - `uv run python -m py_compile layer-tools/websearch-orch/app/main.py`
  - `uv run python -m py_compile scripts/openwebui_phase_a_baseline.py`
- Runtime smoke:
  - `sudo systemctl restart websearch-orch.service`
  - `curl -fsS "http://127.0.0.1:8899/search?q=SearXNG+engine+reliability+guidance+recent+changes+2026&format=json" | jq ...`
  - `journalctl -u websearch-orch.service --since "5 minutes ago" --no-pager | rg -n "fetch_attempts=|fallback_used=|fetch_selected=|fetch_empty_attempts=|fetch_error_attempts="`

### Closeout runs
- `PHASE2-EXIT-007`
  - `run-pack`: `10/10` completed
  - `score-canonical --since "4 hours ago"`: pass
  - Key metrics:
    - `citation_map_ready_rate=0.9216`
    - `grounding_warn_rate=0.0784`
    - `scorable_runs=51`
- `PHASE2-EXIT-008`
  - `run-pack`: `10/10` completed
  - `score-canonical --since "4 hours ago"`: fail
  - Key metrics:
    - `citation_map_ready_rate=0.8228` (gate fail)
    - `grounding_warn_rate=0.1772` (gate fail)
    - `scorable_runs=79`

## Outcome
- Reliability telemetry and fallback behavior are now observable and deterministic.
- Phase 2 is not closed; next round should tighten low-source behavior for weak
  technical-doc/tutorial query variants before rerunning closeout packs.

## Notes
- `layer-tools/websearch-orch/CONSTRAINTS.md` is still absent; proceeded with
  least-risk interpretation per repo guidance.
- `score-canonical` matching is query-text based against `websearch-orch` logs.
  Re-scoring an older run with a broad `--since` window can include later runs
  that used the same canonical prompt pack.
