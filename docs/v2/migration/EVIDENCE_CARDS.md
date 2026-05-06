# V2 Planning Material: Evidence Cards

Not current runtime truth. This is a planning digest of V1 evidence for V2 migration design.

## EC-01
- ID: `EC-01`
- Theme: Gateway control plane
- Lesson: Keep one boring public gateway and derive routing from a single registry/control plane.
- Evidence files: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `docs/journal/2026-02-11-mlx-runtime-single-contract.md`
- Evidence strength: high
- V2 status: doctrine
- What happened: V1 moved to “registry is the source of truth” and had to correct drift caused by split authority between boot config and registry-managed runtime operations.
- V2 implication: Use one authoritative runtime registry plus generated gateway config. Avoid dual sources for boot and live routing.
- Confidence: high

## EC-02
- ID: `EC-02`
- Theme: LiteLLM / GPT formatting
- Lesson: Keep only defect-specific compatibility cleanup in the gateway; do not make the gateway the permanent owner of provider formatting.
- Evidence files: `docs/journal/2026-02-18-litellm-harmony-normalization.md`, `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md`
- Evidence strength: high
- V2 status: doctrine
- What happened: LiteLLM stripped Harmony artifacts to stop turn-history poisoning, but later evidence pushed formatting ownership back upstream and warned against broader gateway formatting.
- V2 implication: Allow narrow emergency shims, but push formatting correctness to the backend and retire generic gateway rewrites.
- Confidence: high

## EC-03
- ID: `EC-03`
- Theme: vLLM-metal / Qwen
- Lesson: Qwen on vLLM-metal only achieved a narrow accepted contract; constrained-tool behavior stayed weak.
- Evidence files: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md`
- Evidence strength: high
- V2 status: historical
- What happened: `main` was accepted only for a narrow non-stream `tool_choice="auto"` path with a LiteLLM recovery hook, while `required` and named forcing remained broken and the shadow stayed `NO-GO`.
- V2 implication: Treat the Qwen/vLLM coding lane as historical caution, not as a presumptive V2 default.
- Confidence: high

## EC-04
- ID: `EC-04`
- Theme: GPT-OSS / llmster / llama.cpp
- Lesson: GPT promotion worked when cutovers used usable-success gates, shared-posture proof, and diagnostic-only raw mirrors.
- Evidence files: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md`, `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`, `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`
- Evidence strength: high
- V2 status: doctrine
- What happened: `deep` moved to shared `8126` only after raw, direct, canary, and public validation. Raw standalone `llama.cpp` stayed diagnostic-first rather than promotion truth.
- V2 implication: Preserve the cutover discipline. Treat the late-V1 GPT-compatible fallback backend as accepted baseline evidence, not as V2 identity. `llmster` belongs in historical implementation evidence only.
- Confidence: high

## EC-05
- ID: `EC-05`
- Theme: Shadow lanes / cutovers
- Lesson: Retire shadow lanes after a decision; do not leave dormant rollout infrastructure pretending to be active surface.
- Evidence files: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`
- Evidence strength: high
- V2 status: doctrine
- What happened: `8123-8125` were still present after the stack settled, then were explicitly retired and removed from active docs.
- V2 implication: Time-box canaries and shadow ports. After cutover, remove them from active truth and policy surfaces.
- Confidence: high

## EC-06
- ID: `EC-06`
- Theme: Studio transport / runtime lanes
- Lesson: LAN-first service-to-service traffic was more durable than tailnet-as-core-runtime.
- Evidence files: `docs/journal/2026-03-10-studio-backend-auth-removal-and-tailnet-boundary.md`, `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`
- Evidence strength: high
- V2 status: doctrine
- What happened: V1 briefly treated tailnet as the canonical Mini↔Studio path, then explicitly superseded it with a simple LAN-first topology after Tailscale drift and breakage.
- V2 implication: Keep operator access and service-to-service transport as separate concerns. Prefer boring local-network paths for core runtime traffic.
- Confidence: high

## EC-07
- ID: `EC-07`
- Theme: OptiLLM / inference-time compute
- Lesson: Inference-time compute should stay opt-in and evidence-gated; promising experiments are not defaults.
- Evidence files: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `docs/journal/2026-02-22-optillm-mlx-server-diff-rebase-and-go.md`, `docs/journal/2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`
- Evidence strength: medium
- V2 status: candidate
- What happened: entropy decoding oscillated between `GO` and `NO_GO` until maintainability was fixed; PlanSearchTrio improved quality when extra reasoning was applied only in synthesis/rewrite.
- V2 implication: Keep opt-in inference-time compute overlays behind explicit overlays or canaries. Apply extra reasoning late, not everywhere.
- Confidence: medium

## EC-08
- ID: `EC-08`
- Theme: oMLX / specialized runtime
- Lesson: Specialized runtime should stay narrow and private; oMLX is an implementation candidate, not a public default.
- Evidence files: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`
- Evidence strength: medium
- V2 status: candidate
- What happened: direct oMLX looked good, but the isolated LiteLLM alias degraded under soak and returned `500`s. The narrow `omlx-runtime` adapter then survived soak and restart with zero failures.
- V2 implication: Preserve the specialized-runtime boundary in V2, but require fresh proof before promoting any concrete oMLX service beyond private or orchestration-facing use.
- Confidence: medium

## EC-09
- ID: `EC-09`
- Theme: OpenHands / sandboxing
- Lesson: OpenHands became acceptable only as a managed local-bind service with operator access and sandbox readiness treated as separate gates.
- Evidence files: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`
- Evidence strength: medium
- V2 status: candidate
- What happened: V1 promoted OpenHands from manual Docker to managed service while preserving `127.0.0.1:4031`, tailnet-only operator access, and no added LAN exposure. Sandbox image readiness remained a separate explicit step.
- V2 implication: Preserve strict execution boundaries. Treat operator UI reachability and worker sandbox readiness as separate acceptance gates.
- Confidence: medium

## EC-10
- ID: `EC-10`
- Theme: MCP / tool sharing
- Lesson: Upstream gateway MCP support was not production-ready merely because control-plane objects existed.
- Evidence files: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`
- Evidence strength: high
- V2 status: historical
- What happened: LiteLLM upstream could register MCP servers/toolsets and list tools, but the actual client-facing MCP routes timed out or returned `500`; result was `NO-GO, rolled back`.
- V2 implication: Treat the LiteLLM-owned shared MCP lane as historical caution unless upstream route and session behavior is re-proven.
- Confidence: high

## EC-11
- ID: `EC-11`
- Theme: Web search / Open WebUI / SearXNG
- Lesson: Native OWUI + SearXNG + `safe_web` was the keeper; custom proxy layers were deleted, then the supported path was hardened.
- Evidence files: `docs/journal/2026-03-07-websearch-supported-path-reset.md`, `docs/journal/2026-04-30-websearch-quality-hardening.md`, `docs/journal/2026-05-01-searxng-reliability-hardening.md`, `docs/journal/2026-04-30-owui-querygen-prompt-policy.md`
- Evidence strength: high
- V2 status: doctrine
- What happened: V1 explicitly removed `websearch-orch`, `fast-research`, and custom LiteLLM schema glue. Later fixes added host-level querygen policy, retrieval hygiene, and bounded fallback without reviving the old stack.
- V2 implication: Start with the supported native path. Improve query generation and retrieval hygiene at the UI boundary before inventing another middle layer.
- Confidence: high

## EC-12
- ID: `EC-12`
- Theme: Vector DB / retrieval / memory
- Lesson: Retrieval discipline matters more than backend brand; source-scoped ingest, rollback, and explicit eval gates must precede any V2 backend default.
- Evidence files: `docs/journal/2026-03-04-studio-main-vector-store-v1.md`, `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`, `docs/journal/2026-03-04-codex-history-pilot-ingest.md`
- Evidence strength: medium
- V2 status: doctrine
- What happened: pgvector was scaffold/planning. QG1 produced no gate-passing candidate. Later Elastic was cut over as the only primary retrieval backend, with pgvector left rollback-only. Codex ingest succeeded because it was redaction-first and delete-by-source.
- V2 implication: Keep source-scoped ingest, explicit eval gates, and clean rollback as doctrine. Treat Elastic only as the late-V1 incumbent candidate requiring V2 quality revalidation.
- Confidence: medium

## EC-13
- ID: `EC-13`
- Theme: Orin voice / XTTS / voice-gateway
- Lesson: The durable speech keeper was the voice facade boundary; XTTS work proved environment readiness only, not a deployable default.
- Evidence files: `docs/journal/2026-03-12-voice-gateway-xtts-runtime-proof-recovery.md`, `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md`
- Evidence strength: medium
- V2 status: doctrine
- What happened: XTTS recovery ended at import/CUDA proof and explicitly said not to treat the proof image as deployment-complete. The live contract stayed centered on `voice-gateway`.
- V2 implication: Keep the speech facade pattern. Treat XTTS or similar backend experiments as subordinate implementation details until they clear real serving gates.
- Confidence: medium

## EC-14
- ID: `EC-14`
- Theme: Monitoring / ops / documentation discipline
- Lesson: High-trust operations depended on localhost-only monitoring, append-only journals, root hygiene, and machine-checked manifests instead of memory.
- Evidence files: `docs/journal/2026-02-09-prometheus-grafana-setup.md`, `docs/journal/2026-02-08-journal-integrity-policy.md`, `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`, `docs/journal/2026-04-02-homelab-durability-eval-loop.md`
- Evidence strength: high
- V2 status: doctrine
- What happened: monitoring stayed localhost-only; journals were append-only; repo root was narrowed to a stable control surface; hygiene decisions shifted toward validator-backed manifests.
- V2 implication: Preserve documentation and hygiene contracts as part of runtime reliability, not as separate process overhead.
- Confidence: high
