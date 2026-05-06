# V2 Planning Material: V2 Migration Notes

Not current runtime truth. This file is a planning seed for V2 migration framing.

## Suggested V2 Starting Posture

- Default to one boring public gateway plus a separate private specialized-runtime lane. Evidence: `docs/foundation/runtime-planes.md` draws that boundary; `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md` validates the specialized adapter narrowly.

- Start V2 from accepted late-V1 defaults, not from every explored branch. Evidence: `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md` and `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md` show where V1 actually landed.

- Preserve evidence-first migration discipline. Evidence: `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md` used raw -> direct -> canary -> public order; `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md` records concrete validation before calling the cutover durable.

## Likely V2 Keepers

- Registry/control-plane generation rather than hand-maintained runtime truth.
- LAN-first service traffic, tailnet-only operator surfaces where appropriate.
- Native OWUI+SearXNG web search with host-visible query/retrieval policy.
- Source-scoped memory ingestion with redaction and explicit rollback.
- Voice facade on Orin rather than direct client-to-backend speech coupling.

Evidence: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `2026-03-16-lan-first-studio-gateway-contract-reset.md`, `2026-05-01-searxng-reliability-hardening.md`, `2026-03-04-codex-history-pilot-ingest.md`, `2026-03-17-voice-gateway-control-plane-doc-hardening.md`.

## Likely V2 Retirements

- Public Qwen `main` lane assumptions.
- Shadow rollout ports as standing infrastructure.
- Custom web-search proxy/schema stack.
- Experimental LiteLLM-owned MCP sharing path.

Evidence: `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`, `2026-03-19-shadow-ports-retired-and-docs-hardened.md`, `2026-03-07-websearch-supported-path-reset.md`, `2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`.

## Re-Test Rather Than Assume

- OptiLLM defaults. V1 has targeted wins, but not broad proof of stable default value. Evidence: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`.

- Elastic retrieval quality. V1 proved runtime cutover durability, but not that all retrieval defaults are final. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `2026-04-29-elastic-vector-db-cutover-runtime.md`.

- oMLX exposure model. Direct and adapter paths looked good; LiteLLM aliasing did not. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`, `2026-04-27-omlx-runtime-phase3-validation.md`.

- OpenHands integration depth. Managed service posture is proven; shared MCP/tooling and broader model experiments are not. Evidence: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`, `2026-04-15-qwen-agent-proxy-openhands-shadow-slice.md`, `2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`.

## Documentation Carry-Forward Rules

- V2 planning docs must stay clearly marked as planning-only, not runtime truth. Evidence: `docs/_core/SOURCES_OF_TRUTH.md` puts journals and future-looking notes below authoritative docs.

- Preserve append-only journal behavior and narrow root control surface during migration. Evidence: `docs/journal/README.md`, `docs/journal/2026-02-08-journal-integrity-policy.md`, `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`.

- For hygiene tasks, trust machine-checked manifests over memory. Evidence: `docs/journal/2026-04-02-homelab-durability-eval-loop.md`.

## Needs Human/ChatGPT Review

- Should V2 treat late-V1 GPT `llmster` architecture as the direct baseline, or abstract it one level higher and re-select the concrete backend later?
- Should V2 include a specialized-runtime plane from day one, or preserve only the boundary and defer the concrete oMLX decision?
- Should V2 memory default to Elastic immediately, or rerun a slim bake-off with explicit quality gates before locking that in?
