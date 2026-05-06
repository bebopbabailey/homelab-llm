# V2 Planning Material: V2 Migration Notes

Not current runtime truth. This file is a planning seed for V2 migration framing.

## Resolved V2 Starting Posture

- V2 starts from one boring public gateway plus a separate specialized-runtime architectural boundary. Evidence: `docs/foundation/runtime-planes.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`
- V2 inherits accepted late-V1 baselines and cutover discipline, not every explored branch or naming artifact. Evidence: `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`, `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`
- V2 keeps evidence-first migration discipline: raw -> direct -> canary -> public when a new runtime path needs promotion. Evidence: `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`, `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`

## Accepted V1 Baseline vs V2 Identity

- The late-V1 GPT-compatible fallback backend is the latest accepted V1 compatibility baseline, not the V2 identity or automatic default. Historical implementation evidence includes `llmster`. Evidence: `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`, `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`
- V2 doctrine is registry-derived routing, LAN-first service traffic, native OWUI + SearXNG search, source-scoped memory discipline, and a speech facade boundary. Evidence: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`, `docs/journal/2026-05-01-searxng-reliability-hardening.md`, `docs/journal/2026-03-04-codex-history-pilot-ingest.md`, `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md`

## Candidate Implementations Requiring Revalidation

- Elastic is the incumbent retrieval backend candidate, but V2 doctrine is retrieval discipline first; backend choice must pass a slimmer V2 quality gate. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`
- The specialized-runtime plane belongs in V2 architecture on day one, but no concrete specialized-runtime service is required in phase one. Evidence: `docs/foundation/runtime-planes.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`
- Opt-in inference-time compute overlays survive only as an implementation candidate pattern, with historical OptiLLM evidence informing that candidate. Evidence: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `docs/journal/2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`
- OpenHands remains a conditional candidate whose managed local-bind posture is proven, while broader integration depth remains unproven. Evidence: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`, `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`

## Historical Retirements

- Public Qwen `main` lane assumptions are historical only. Evidence: `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`
- Standing shadow rollout ports are historical only. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`
- Custom web-search proxy and schema glue are historical only. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md`
- Experimental LiteLLM-owned MCP sharing assumptions are historical only. Evidence: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`
