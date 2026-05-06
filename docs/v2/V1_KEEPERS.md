# V2 Planning Material: V1 Keepers

Not current runtime truth. These are V1 patterns sorted by how strongly they should influence V2 planning.

## Accepted V2 Doctrine

- One boring public gateway with narrow aliases and clear ownership boundaries. Evidence: `README.md`, `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`
- Registry-driven runtime/gateway synchronization. Evidence: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `docs/journal/2026-02-11-mlx-runtime-single-contract.md`
- LAN-first Mini↔Studio service traffic. Evidence: `docs/foundation/topology.md`, `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`
- Specialized-runtime plane as an architectural boundary. Evidence: `docs/foundation/runtime-planes.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`
- Native Open WebUI + SearXNG + `safe_web` search path. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md`, `docs/journal/2026-05-01-searxng-reliability-hardening.md`
- Host-visible query-generation and retrieval-hygiene policy. Evidence: `docs/journal/2026-04-30-owui-querygen-prompt-policy.md`, `docs/journal/2026-04-30-websearch-quality-hardening.md`
- Source-scoped, redaction-first memory ingest with rollback. Evidence: `docs/journal/2026-03-04-codex-history-pilot-ingest.md`
- Speech facade pattern. Evidence: `docs/foundation/topology.md`, `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md`
- Localhost-only monitoring with repo-managed deployed config. Evidence: `docs/journal/2026-02-09-prometheus-grafana-setup.md`, `docs/INTEGRATIONS.md`
- Append-only journal discipline. Evidence: `docs/journal/README.md`, `docs/journal/2026-02-08-journal-integrity-policy.md`
- Narrow repo-root control surface. Evidence: `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`, `README.md`
- Worktree-first mutable-work discipline. Evidence: `AGENTS.md`, `docs/OPENCODE.md`

## Conditional V2 Candidates

- Late-V1 GPT-compatible fallback backend as accepted V1 compatibility baseline, not V2 identity. Historical implementation evidence includes `llmster`. Evidence: `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`, `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`
- Concrete `omlx-runtime` service as a specialized-runtime implementation candidate. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`
- Elastic as incumbent retrieval backend candidate requiring quality revalidation. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`
- Opt-in inference-time compute overlays as an implementation candidate only. Historical implementation evidence includes OptiLLM. Evidence: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `docs/journal/2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`
- Managed OpenHands service with local bind and tailnet-only operator access. Evidence: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`
- Memory API read/search vs write-token boundary if V2 keeps a similar memory-service split. Evidence: `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`, `docs/INTEGRATIONS.md`

## Historical Reference Only

- Gateway cleanup hooks as narrow V1 rescue tactics, not preferred V2 design. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md`
- Public Qwen/vLLM `main` lane assumptions. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`
- V1 `boost-*` profile names and similar alias-era vocabulary. Evidence: `docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md`
- Temporary GPT rollout and shadow alias vocabulary. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`, `docs/INTEGRATIONS.md`

## Needs Human/ChatGPT Review

- Whether OpenHands belongs in V2 phase-one scope at all, even if its local-bind and operator-boundary posture stays intact.
