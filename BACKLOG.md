# BACKLOG

Short list of future work not active right now.

## Paused from NOW
- Web-search review packet cleanup:
  - Consolidate the current promptfoo lane-comparison materials into one reviewer-friendly directory.
  - Generate a single review packet so manual scoring does not require digging through raw JSON artifacts.
  - Keep the work limited to evaluation/review surfaces; no runtime config or provider changes.

## Docs cleanup waves (deferred)
- Wave B: canonical boundary tightening (summary docs point to canon, reduce duplication).
- Wave C: temporal relocation/lifecycle policy (snapshot-style docs moved to proper historical buckets).
- Wave D: foundation taxonomy split (canonical contracts vs operator guides vs evaluation/fixtures).

## Nice-to-haves
- Vector-db eval harness refactor:
  - Replace handwritten IR metric math with `ir-measures` + pinned provider support.
  - Re-key judgments by `(query_id, chunk_id)` so labels survive reranking.
  - Keep `run-pack` / `autolabel` / `triage` / `label` / `score` workflow stable while updating docs/tests to the new metric engine.
- Promptfoo web-search eval hardening:
  - Add deterministic promptfoo assertions for empty output, blocked domains, and expected grounding.
  - Track the eval-only blocked-domain policy separately from runtime config.
  - Tighten `owui-fast` vs `owui-research` comparison reporting before any provider bakeoff.
- Transcribe helper restoration:
  - Restore `config/transcribe_utils.py` as the shared cleanup helper surface.
  - Rebind `transcribe_guardrail.py` to shared helpers instead of copied local logic.
  - Recover `tests/test_transcribe_baseline.py` and lock wrapper/punctuation semantics.
- PlanSearchTrio forensic handoff audit:
  - Build implementation-only file inventory with stage timeline and risk surface map for associate review.
- PlanSearchTrio blind quality-gate tooling:
  - Add reproducible A/B capture + blind-packet + scorer scripts.
  - Wire canonical runbook/testing docs for 50-prompt human rubric gate.
  - Add grading accelerator sheet (`ab_grade_assist.py`) and numeric CLI (`ab_quick_grade.py`) for faster human review.
  - Soft-promote OpenCode default to `boost-plan-trio` with explicit fallback to `boost-plan`.
- Vector-db future eval tooling:
  - If still desired after drift repair, add `autolabel` and `triage` to the tracked eval script as a separate feature cycle.
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
