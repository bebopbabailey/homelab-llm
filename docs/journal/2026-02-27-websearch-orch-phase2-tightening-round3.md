# 2026-02-27 — websearch-orch Phase 2 tightening (round 3)

## Summary
- Implemented Phase 2 quality-tightening controls focused on drift reduction and source trust.
- Added query/entity guardrails to sanitize conflicting query variants before SearXNG fetch.
- Added trust-tier scoring/ordering metadata so weak domains are deprioritized and observable.
- Kept Phase 2 calibration controls intact (bounded loader budget, fair-share slices).

## Repo changes
- Updated `layer-tools/websearch-orch/app/main.py`:
  - Added query guard config and conflict detection (`QUERY_GUARD_ENABLED`, `QUERY_ENTITY_CONFLICT_ACTION`).
  - Added trust policy config + scoring (`TRUST_*` vars).
  - Added minimum snippet guard (`MIN_RESULT_CONTENT_CHARS`).
  - Added response metadata:
    - `query_guard`
    - `trust_summary`
    - `grounding` (source URLs/count)
    - per-result `orch_source_id`, `orch_source_url`, `orch_trust_tier`.
  - Added structured logs for `guarded_query`, `query_action`, `conflicts`, `trust`.
- Updated `layer-tools/websearch-orch/config/env.example` with new tightening vars.
- Updated docs:
  - `layer-tools/websearch-orch/RUNBOOK.md`
  - `docs/foundation/testing.md`
  - `docs/PLATFORM_DOSSIER.md`
  - `NOW.md`
  - `BACKLOG.md`

## Runtime changes (Mini)
- Backed up `/etc/homelab-llm/websearch-orch.env`:
  - `/etc/homelab-llm/websearch-orch.env.bak.20260227-201237`
- Applied explicit tightening vars:
  - `QUERY_GUARD_ENABLED=true`
  - `QUERY_ENTITY_CONFLICT_ACTION=sanitize`
  - `TRUST_POLICY_ENABLED=true`
  - `TRUST_PRIORITY_DOMAINS=...`
  - `TRUST_DEPRIORITIZED_DOMAINS=...`
  - `TRUST_DROP_BELOW_SCORE=-2`
  - `MIN_RESULT_CONTENT_CHARS=60`
- Restarted:
  - `sudo systemctl restart websearch-orch.service`

## Validation
- `python3 -m py_compile layer-tools/websearch-orch/app/main.py` passed.
- `systemctl is-active websearch-orch.service` => `active`.
- `curl http://127.0.0.1:8899/health` => healthy.
- Conflict-query smoke test:
  - Input: `Instrument methods used in NASA Chang’e-6 to detect water`
  - Output `query_guard.action=sanitize`
  - Effective query: `Instrument methods used in Chang’e-6 to detect water`
  - Trust summary present with tier counts.
- Normal-query smoke test:
  - `query_guard.action=pass`
  - `trust_summary` present.
- Journal log check confirmed new log fields:
  - `guarded_query=... query_action=... conflicts=... trust=...`

## Notes
- This round tightens retrieval quality controls; it does not add vector stores or schema synthesis.
- Phase 2 remains active until end-user Open WebUI loops show consistent non-fabricated citations and stable relevance.
