# BACKLOG

Short list of future work not active right now.

## Web Search Quality Roadmap (Canonical)
- Baseline (Completed):
  - Open WebUI Phase A baseline harness and scoring workflow are in place.
  - References: `docs/journal/2026-02-18-openwebui-websearch-phase-a-baseline.md`,
    `docs/foundation/testing.md`.
- Phase 1 (Completed):
  - Local semantic reranker integrated in `websearch-orch` with fail-open
    behavior and service runbook wiring.
  - Reference: `docs/journal/2026-02-21-websearch-orch-local-reranker-phase1.md`.
- Phase 2 (Active, in validation):
  - Calibration Gate: extraction-size control + reranker calibration + strict
    validation gate.
  - Implemented:
    - `websearch-orch` per-document extraction cap
    - `websearch-orch` total-response extraction budget cap
    - telemetry for `raw_chars`, `doc_caps`, `budget_caps`, `budget_drops`
    - round-2 fair-share budget allocation across sources
    - round-2 loader fanout cap (`EXTERNAL_WEB_LOADER_MAX_URLS=12`)
    - round-3 query/entity guardrails for conflicting rewritten intents
    - round-3 source trust policy (priority/deprioritized tiering + trust summary)
    - round-3 grounding metadata (`orch_source_id`, `orch_trust_tier`, source URL list)
    - round-4 citation contract metadata (`citation_map_status`, `allowed_urls`, source map)
    - round-4 duplicate-title suppression and per-domain source cap in search filtering
    - round-4 tighter trust drop threshold (`TRUST_DROP_BELOW_SCORE=-1`)
    - round-4 quality telemetry (`dedupe_drops`, `domain_cap_drops`, `placeholder_drops`)
    - round-5 tighter retrieval defaults (`MAX_TEXT=2800`, `MAX_TOTAL=18000`, `MAX_URLS=10`, `MIN_PER_DOC=700`)
    - round-5 stricter baseline trust/content thresholds (`TRUST_DROP_BELOW_SCORE=0`, `MIN_RESULT_CONTENT_CHARS=160`)
    - round-5 grounding gate payload and log telemetry (`grounding_status`, `grounding_allowed_urls`)
    - round-5 Phase A scorer extension with Phase 2 quality metrics
    - Open WebUI middleware hardening for web-search query generation payload normalization (`JSONResponse`/dict compatibility)
    - post-outage trail recovery validation (`8100/8101/8102` reachability restored; `main/deep/fast/boost` non-stream chat smokes pass; no fresh LiteLLM upstream connection errors in recovery window)
  - Exit criteria:
    1. No retrieval stability regressions in Phase A scoring.
    2. Lower oversized-context incidence in Open WebUI search traces.
    3. Consistent `websearch-orch` rerank telemetry without fail-open churn.
    4. No drifted entity query variants reaching retrieval (`query_action=sanitize/reject`).
    5. No fabricated citation placeholders in repeated end-user citation prompts.
    6. `citation_map_status=ready` for grounded runs with >=2 valid sources.
    7. `grounding_gate.status=warn` remains rare (target <=10% of grounded runs).
  - Current checkpoint:
    - Recovery run-id `RECOVERY-20260303-A` created for Phase A.
    - Score script currently shows 0/10 seen because the query pack has not yet been executed in Open WebUI with run-id markers.
- Phase 3 (Queued):
  - Structured output/synthesis layer (schema-first output contract after
    retrieval stage).
  - DSPy follow-on: expand citation-fidelity eval set and promote compiled
    policy behind a feature flag only after repeatable pass-rate gains.
- Phase 4 (Queued, Optional):
  - Vector-store-assisted retrieval/reranking, evaluated only after
    Phase 2/3 are stable.

## Docs cleanup waves (deferred)
- Wave B: canonical boundary tightening (summary docs point to canon, reduce duplication).
- Wave C: temporal relocation/lifecycle policy (snapshot-style docs moved to proper historical buckets).
- Wave D: foundation taxonomy split (canonical contracts vs operator guides vs evaluation/fixtures).

## Nice-to-haves
 - Harden Studio OptiLLM proxy for remote maintenance (tailnet-only serve: bind localhost + Tailscale Serve + LiteLLM upstream update).
- Confirm current alias policy remains documented consistently (`main`/`deep`/`fast` stable; `metal-test-*` temporary experimental labels; no active `swap*` usage).
- Validate preset behavior via LiteLLM/OptiLLM (routing, chain applied, responses).
- [mlxctl] Optional symmetry: if running `mlxctl sync-gateway` on the Studio, auto-forward to the gateway host (Mini) instead of requiring you to hop hosts manually. Would require a `GATEWAY_SSH` (or similar) and a `_maybe_forward_to_gateway()` that mirrors `_maybe_forward_to_studio()`. Not required for correctness; ergonomics only.
- [mlxctl] Phase-2 schema hardening: migrate all active entries to canonical nested `vllm` blocks and deprecate flat `vllm_*` key writes after compatibility window.
- [studio-reboot] Mini-side automation for post-reboot Studio recovery: wake/retry loop, SSH preflight classification (`HOST_DOWN`/`LOCKED`/`AUTH_REJECTED`), and operator prompting until team lanes are reachable again.
- [LiteLLM] Optional “lane-policy” pre_call guardrail: enforce that `optillm_approach`/`optillm_base_model` are only accepted when `model=boost`, and reject `decoding=*` on `boost` (decode-loop requests should route directly to Omni). Not required for correctness; ergonomics/safety only.
- Keep OpenCode config aligned with current handles and tool access.
- Open WebUI preset sync from LiteLLM presets.
- Enable LiteLLM UI access so client-side system prompts/presets can be managed there.
- Standardize per-user Node.js toolchain via Volta (avoid sudo/EACCES; future user onboarding).
- Formalize a presets registry (JSONL + validator + CLI).
- Document SDLC mapping and usage guidance.
- Transcript pipeline service (server-side chaining, stateless + stateful interviewer, SQLite persistence, strict JSON outputs).
- Inference benchmarking framework (latency/quality journal automation).
- Model table design (database-backed, size-on-disk + idle-memory fields).
- OptiLLM local inference (Orin AGX, CUDA) for decode-time techniques.
- Optional second-pass tone classification for transcripts (separate endpoint).
- OpenVINO re-think (if ever): capture design notes here first, not in canonical docs; only proceed with explicit decision + migration plan.
- OptiLLM router caching follow-up (re-verify after any OV work).
