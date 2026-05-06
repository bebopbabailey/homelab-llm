# V2 Planning Material: V1 Lessons Learned

Not current runtime truth. This is a migration-planning synthesis from V1 evidence.

## Proven Lessons

- One control plane beats split authority. Evidence: `docs/journal/2026-02-11-mlx-runtime-single-contract.md` says drift on `8101` came from “split authority”; `docs/journal/2026-01-18-mlx-sync-gateway.md` says gateway entries should exist only for loaded models with ports.

- The public contract should stay boring even if backend experiments are not. Evidence: `docs/foundation/runtime-planes.md` separates commodity inference from specialized runtime; `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md` recommends `omlx-runtime` only as a “stable specialized-runtime portal,” not public routing.

- GPT promotion worked when gated by usable outcomes, not perfection. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md` defined a usable-success gate; `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md` accepted `deep` with `required` strong while named forcing stayed unsupported.

- Raw mirrors are diagnostic seams, not automatic promotion oracles. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md` says raw `llama.cpp` is “diagnostic-first”; `docs/INTEGRATIONS.md` says raw mirrors are loopback-only truth-path mirrors, not public contract.

- Narrow gateway shims are acceptable; broad compatibility magic is not. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md` accepted a `main`-only narrow post-call recovery; `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md` warns not to add a general GPT Harmony formatter in LiteLLM.

- Tailnet is useful operator access, but a poor foundation for core service-to-service truth when LAN is available. Evidence: `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md` explicitly supersedes the earlier tailnet-only boundary from `docs/journal/2026-03-10-studio-backend-auth-removal-and-tailnet-boundary.md`.

- Web search improved when V1 deleted custom glue instead of preserving it. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md` says the supported-path reset “intentionally deletes that stack”; later entries (`2026-04-30`, `2026-05-01`) harden the native OWUI+SearXNG path rather than revive `websearch-orch`.

- Retrieval substrate bring-up and retrieval quality are separate problems. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md` reports “no gate-passing candidate” even after QG1 execution; `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md` proves backend durability and auth but does not claim evaluation is unnecessary.

- Source-scoped memory ingest and redaction-first design are durable patterns. Evidence: `docs/journal/2026-03-04-codex-history-pilot-ingest.md` used deterministic IDs, secret redaction, sensitive-reference guards, and “rollback by source.”

- Runtime experiments need crisp closure: promote, retire, or roll back. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md` retired stale shadow ports; `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md` retired `main`; `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md` stopped the alias path after soak failures.

- Documentation discipline is part of system reliability. Evidence: `docs/journal/2026-02-08-journal-integrity-policy.md` makes journals append-only; `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md` narrows root; `docs/journal/2026-04-02-homelab-durability-eval-loop.md` says machine-checked manifests should outrank memory.

## Tentative Hypotheses

- OptiLLM can help coding/planning lanes, but only as explicit overlays. Evidence: `docs/journal/2026-03-03-optillm-coding-profiles-vllm-metal.md` added `boost-*` coding aliases; `docs/journal/2026-03-06-plansearchtrio-reasoning-effort-synthesis.md` found late-stage reasoning effort worthwhile. Hypothesis: V2 may want profile overlays, not default always-on inference-time compute.

- Elastic is the strongest late-V1 retrieval backend, but V2 should still re-earn the default. Evidence: `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md` promotes Elastic to primary and demotes pgvector to rollback only. Hypothesis: V2 should start with Elastic as the leading candidate, not unquestioned doctrine.

- A specialized runtime plane may be valuable for orchestration and cache-sensitive workflows. Evidence: `docs/foundation/runtime-planes.md` and `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`. Hypothesis: V2 could formalize this plane earlier, but only if it stays narrow and private.

## Needs Human/ChatGPT Review
- Whether V2 should preserve any public concept equivalent to V1 `boost-*` profiles.
- Whether V2 should carry over LiteLLM post-call cleanup hooks at all or treat them as V1 debt to re-test away.
- Whether V2 should keep a dedicated speech facade identical to V1 `voice-gateway` or redesign that boundary while preserving the facade principle.
