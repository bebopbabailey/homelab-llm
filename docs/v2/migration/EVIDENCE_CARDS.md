# V2 Planning Material: Evidence Cards

Not current runtime truth. This is a planning digest of V1 evidence for V2 migration design.

## EC-01
- Theme: Gateway control plane
- Lesson: Keep one boring public gateway and derive routing from a single registry/control plane.
- Evidence files: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `docs/journal/2026-02-11-mlx-runtime-single-contract.md`
- What happened: V1 moved to “registry is the source of truth” and then had to correct drift caused by “split authority between hardcoded launchd boot config and registry-managed runtime operations.”
- V2 implication: Use one authoritative runtime registry plus generated gateway config. Avoid dual sources for boot and live routing.
- Confidence: high

## EC-02
- Theme: LiteLLM / GPT formatting
- Lesson: Put only defect-specific compatibility cleanup in the gateway; do not make the gateway the permanent owner of provider formatting.
- Evidence files: `docs/journal/2026-02-18-litellm-harmony-normalization.md`, `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md`
- What happened: LiteLLM had to strip Harmony artifacts to stop “turn-history poisoning,” but later evidence said “upstream llmster is the formatting owner” and warned “do not add a broader Harmony formatter.”
- V2 implication: Allow narrow emergency shims, but plan to push formatting correctness to the backend and retire generic gateway rewrites.
- Confidence: high

## EC-03
- Theme: vLLM-metal / Qwen
- Lesson: Qwen on vLLM-metal only achieved a narrow accepted contract; forced-tool and exact schema support stayed weak.
- Evidence files: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md`
- What happened: `main` was accepted only for non-stream `tool_choice="auto"` with a narrow LiteLLM post-call recovery hook, while `required` and named tool forcing remained broken on shadow validation and the shadow stayed `NO-GO`.
- V2 implication: Do not make Qwen/vLLM the default constrained-tool coding lane without fresh evidence. Treat it as historical, not presumptive canon.
- Confidence: high

## EC-04
- Theme: GPT-OSS / llmster / llama.cpp
- Lesson: GPT promotion succeeded when the contract used a usable-success gate, shared-posture proof, and a diagnostic-only raw mirror.
- Evidence files: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md`, `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`, `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`
- What happened: `deep` moved to shared `8126` only after raw, direct, canary, and public validation. Raw standalone `llama.cpp` was kept “diagnostic-first,” not promotion truth by itself.
- V2 implication: Preserve multi-step cutover discipline. Prefer a stable shared GPT runtime over speculative per-lane novelty when it proves operationally sufficient.
- Confidence: high

## EC-05
- Theme: Shadow lanes / cutovers
- Lesson: Retire shadow lanes after a decision; do not leave dormant rollout infrastructure pretending to be part of the active surface.
- Evidence files: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`
- What happened: `8123-8125` were still present after the stack settled, then were explicitly retired and removed from active docs.
- V2 implication: Time-box canaries and shadow ports. After cutover, remove them from active truth and policy surfaces.
- Confidence: high

## EC-06
- Theme: Studio transport / runtime lanes
- Lesson: LAN-first service-to-service traffic was more durable than tailnet-as-core-runtime.
- Evidence files: `docs/journal/2026-03-10-studio-backend-auth-removal-and-tailnet-boundary.md`, `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`
- What happened: V1 briefly treated tailnet as the canonical Mini↔Studio path, then explicitly superseded that with a “simple LAN-first topology” after Tailscale drift and breakage.
- V2 implication: Keep operator access and service-to-service transport as separate concerns. Prefer boring local-network paths for core runtime traffic.
- Confidence: high

## EC-07
- Theme: OptiLLM / inference-time compute
- Lesson: Inference-time compute should stay opt-in and evidence-gated; promising experiments are not defaults.
- Evidence files: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `docs/journal/2026-02-22-optillm-mlx-server-diff-rebase-and-go.md`, `docs/journal/2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`
- What happened: entropy decoding oscillated between `GO` and `NO_GO` until maintainability was fixed; PlanSearchTrio improved quality when `reasoning_effort=high` was applied only in synthesis/rewrite.
- V2 implication: Keep compute-intensifying approaches behind explicit profiles/canaries. Apply extra reasoning late, not everywhere.
- Confidence: medium

## EC-08
- Theme: oMLX / specialized runtime
- Lesson: Direct oMLX and the narrow adapter looked stable; LiteLLM aliasing in front of oMLX did not.
- Evidence files: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`
- What happened: direct oMLX was strong, but the isolated LiteLLM alias degraded under soak and returned `500`s. The narrow `omlx-runtime` adapter then survived soak and restart with zero failures.
- V2 implication: If V2 wants oMLX, preserve it as a private specialized-runtime portal, not a public gateway alias by default.
- Confidence: high

## EC-09
- Theme: OpenHands / sandboxing
- Lesson: OpenHands became acceptable only as a managed local-bind service with separate operator access and explicit sandbox follow-up.
- Evidence files: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`
- What happened: V1 promoted OpenHands from manual Docker to managed service while preserving `127.0.0.1:4031`, tailnet-only operator access, and “no LAN exposure added.” The sandbox image still remained a separate explicit step.
- V2 implication: Preserve strict execution boundaries. Treat operator UI reachability and worker sandbox readiness as separate acceptance gates.
- Confidence: high

## EC-10
- Theme: MCP / tool sharing
- Lesson: Do not assume upstream gateway MCP support is production-ready just because control-plane objects exist.
- Evidence files: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`
- What happened: LiteLLM upstream could register MCP servers/toolsets and list tools, but the actual client-facing MCP routes timed out or returned `500`; result was `NO-GO, rolled back`.
- V2 implication: Avoid making a shared LiteLLM-owned MCP lane a core V2 dependency unless upstream route/session behavior is re-proven.
- Confidence: high

## EC-11
- Theme: Web search / Open WebUI / SearXNG
- Lesson: Native OWUI + SearXNG + `safe_web` was the keeper; custom proxy layers were deleted, then OWUI-side hardening made the supported path safer.
- Evidence files: `docs/journal/2026-03-07-websearch-supported-path-reset.md`, `docs/journal/2026-04-30-websearch-quality-hardening.md`, `docs/journal/2026-05-01-searxng-reliability-hardening.md`, `docs/journal/2026-04-30-owui-querygen-prompt-policy.md`
- What happened: V1 explicitly removed `websearch-orch`, `fast-research`, and custom LiteLLM schema glue. Later fixes added host-level querygen policy, retrieval hygiene, and bounded fallback without reviving the old stack.
- V2 implication: Start with the supported native path. Improve query generation and retrieval hygiene at the UI boundary before inventing another middle layer.
- Confidence: high

## EC-12
- Theme: Vector DB / retrieval / memory
- Lesson: pgvector was a scaffold; Elastic became the accepted primary backend, but retrieval quality still required explicit evaluation and source-scoped ingest discipline.
- Evidence files: `docs/journal/2026-03-04-studio-main-vector-store-v1.md`, `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`, `docs/journal/2026-03-04-codex-history-pilot-ingest.md`
- What happened: initial pgvector work was scaffold/planning. QG1 produced “no gate-passing candidate” under provisional scoring. Later Elastic was cut over as “the only primary retrieval backend,” with pgvector left “rollback only.” Codex ingest succeeded because it was redaction-first and delete-by-source.
- V2 implication: Use source-scoped ingest, explicit eval gates, and clean rollback. Do not infer retrieval quality from backend bring-up alone.
- Confidence: high

## EC-13
- Theme: Orin voice / XTTS / voice-gateway
- Lesson: The durable V1 speech keeper was the live `voice-gateway`; XTTS work proved environment readiness only, not a deployable default.
- Evidence files: `docs/journal/2026-03-12-voice-gateway-xtts-runtime-proof-recovery.md`, `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md`
- What happened: XTTS recovery ended at import/CUDA proof and explicitly said “do not treat the proof image as deployment-complete.” Meanwhile the live contract was documented around `voice-gateway` on Orin `:18080`.
- V2 implication: Keep the speech facade pattern. Treat XTTS or similar backend experiments as subordinate implementation details until they clear real serving gates.
- Confidence: high

## EC-14
- Theme: Monitoring / ops / documentation discipline
- Lesson: High-trust operations depended on localhost-only monitoring, append-only journals, root hygiene, and machine-checked manifests instead of memory.
- Evidence files: `docs/journal/2026-02-09-prometheus-grafana-setup.md`, `docs/journal/2026-02-08-journal-integrity-policy.md`, `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`, `docs/journal/2026-04-02-homelab-durability-eval-loop.md`
- What happened: monitoring was kept localhost-only; journals were locked append-only; repo root was narrowed to a stable control surface; hygiene decisions were shifted toward validator-backed manifests.
- V2 implication: Preserve disciplined documentation contracts as part of runtime reliability, not as separate “process overhead.”
- Confidence: high

## Needs Human/ChatGPT Review
- Whether EC-07 is strong enough to preserve any specific OptiLLM default in V2, or only the pattern of staged/canary compute overlays.
- Whether EC-12 should be read as “Elastic default” for V2, or “Elastic was V1’s latest accepted backend and should be revalidated from first principles.”
- Whether EC-08’s private specialized-runtime portal should remain an orchestration-only concern or become a broader V2 substrate later.
