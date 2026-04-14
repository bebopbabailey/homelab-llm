# Tasks: Vector DB (Studio Main Store)

## Completed
- [x] Service/API architecture and docs baseline.
- [x] SQL schema for docs/chunks/vectors/ingest runs.
- [x] Studio launchd templates + policy wiring for owned labels.
- [x] Deploy/install scripts and runbook wiring for Studio utility wrapper.
- [x] Baseline smoke-tested ingest/search/backup path documented.
- [x] Codex history pilot corpus builder (`build_codex_history_pilot.py`) with deterministic IDs and secret redaction.
- [x] QG1 evaluation scaffold (fixed query pack, judgment template, scoring helper).
- [x] Conservative auto-label + triage workflow for docs retrieval gate.
- [x] Backend abstraction (`legacy|haystack`) with contract-preserving API handlers.
- [x] Haystack backend core retrieval path (keyword+vector+RRF+optional rerank).
- [x] Haystack schema bootstrap script (`scripts/init_haystack_schema.py`).
- [x] Ingest mode split (`jsonl` + `manuals_pdf`) with backend-aware writer path.

## Next
- [ ] Validate Haystack backend end-to-end on Studio (`/health`, stats, upsert, search, delete).
- [ ] Run side-by-side quality check against legacy baseline before cutover.
- [ ] Expand docs negative-control pack after the first auto-label pass stabilizes.
- [ ] Enable `MEMORY_BACKEND=haystack` on Studio service env and monitor.
- [ ] Decide default search strategy (`hnsw` vs fallback exact) after first boot on Studio.
- [ ] Lock reranker model after latency/quality pass.
- [ ] Implement retention + compaction contract (daily/weekly/monthly windows).
- [ ] Add restore drill script and parity query checks.
