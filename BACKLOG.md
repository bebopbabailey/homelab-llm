# BACKLOG

Short list of future work not active right now.

## Docs cleanup waves (deferred)
- Wave B: canonical boundary tightening (summary docs point to canon, reduce duplication).
- Wave C: temporal relocation/lifecycle policy (snapshot-style docs moved to proper historical buckets).
- Wave D: foundation taxonomy split (canonical contracts vs operator guides vs evaluation/fixtures).

## Nice-to-haves
 - Harden Studio OptiLLM proxy for remote maintenance (tailnet-only serve: bind localhost + Tailscale Serve + LiteLLM upstream update).
- Confirm alias naming and mapping (main / deep / fast / swap, + x1..x4).
- Validate preset behavior via LiteLLM/OptiLLM (routing, chain applied, responses).
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
