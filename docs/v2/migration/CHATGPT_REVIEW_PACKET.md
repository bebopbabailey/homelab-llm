# V2 Planning Material: ChatGPT Review Packet

Not current runtime truth. This is a compressed review packet for the V2 migration seed set. Canonical current runtime truth remains the active platform, integration, topology, and service docs named in `docs/_core/SOURCES_OF_TRUTH.md`.

## 1. Executive Summary

- The V2 seed set is directionally sound: it correctly separates current canon from planning material, centers durable operating lessons over chronology, and does not treat journals as runtime truth. Evidence: `docs/_core/SOURCES_OF_TRUTH.md`, `docs/v2/migration/JOURNAL_MAP.md`.
- The strongest late-V1 durable patterns were: one boring public gateway, registry-driven control plane, LAN-first Mini↔Studio traffic, native OWUI+SearXNG search, source-scoped redaction-first retrieval ingest, and a separate specialized-runtime boundary. Evidence: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `2026-02-11-mlx-runtime-single-contract.md`, `2026-03-16-lan-first-studio-gateway-contract-reset.md`, `2026-03-07-websearch-supported-path-reset.md`, `2026-03-04-codex-history-pilot-ingest.md`, `docs/foundation/runtime-planes.md`.
- The hardest V1 lessons were negative: do not keep shadow lanes alive after decisions, do not trust direct-backend success as proof of gateway success, do not revive custom web-search glue, and do not promote experimental systems before strong acceptance evidence. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`, `2026-04-21-omlx-litellm-shadow-alias-result.md`, `2026-03-07-websearch-supported-path-reset.md`, `2026-02-19-optillm-mlx-viability-testing-log.md`.
- The seed set is still too repetitive. The same conclusions currently appear across `EVIDENCE_CARDS`, `V1_LESSONS_LEARNED`, `V1_KEEPERS`, and `V2_MIGRATION_NOTES`, and some “keeper” language is still too close to “candidate default” language. Evidence: `docs/v2/migration/EVIDENCE_CARDS.md`, `docs/v2/V1_LESSONS_LEARNED.md`, `docs/v2/V1_KEEPERS.md`, `docs/v2/V2_MIGRATION_NOTES.md`.

## 2. Top 20 Durable V1 Lessons

1. One control plane beats split authority. Evidence: `docs/journal/2026-02-11-mlx-runtime-single-contract.md`, `2026-01-18-mlx-sync-gateway.md`.
2. Public inference and specialized runtime should stay separate. Evidence: `docs/foundation/runtime-planes.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`.
3. Gateway config should be derived from registry/runtime truth, not hand-maintained separately. Evidence: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `docs/INTEGRATIONS.md`.
4. GPT cutovers should use usable-success gates, not perfection gates. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md`, `2026-03-19-public-deep-cutover-to-shared-8126.md`.
5. Raw mirrors are diagnostic seams, not promotion oracles. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md`, `docs/INTEGRATIONS.md`.
6. Narrow gateway shims are acceptable only when the defect is proven and scoped. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `2026-04-22-gptoss-harmony-upstream-fix.md`.
7. LAN-first service-to-service transport is more durable than tailnet-as-runtime-core. Evidence: `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`, `docs/foundation/topology.md`.
8. Shadow lanes must be retired after decisions, not left as dormant “maybe later” infrastructure. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`.
9. Qwen/vLLM achieved only a narrow accepted contract and was later retired from production. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`.
10. Native OWUI+SearXNG+`safe_web` is the supported search path; extra proxy/schema glue created drift. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md`, `docs/foundation/topology.md`.
11. Search quality should be improved at the UI/retrieval boundary before inventing new middleware. Evidence: `docs/journal/2026-04-30-websearch-quality-hardening.md`, `2026-05-01-searxng-reliability-hardening.md`, `2026-04-30-owui-querygen-prompt-policy.md`.
12. Retrieval substrate bring-up and retrieval-quality acceptance are separate gates. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `2026-04-29-elastic-vector-db-cutover-runtime.md`.
13. Source-scoped, redaction-first ingest is a keeper pattern for memory/retrieval. Evidence: `docs/journal/2026-03-04-codex-history-pilot-ingest.md`.
14. Elastic was accepted as late-V1 primary retrieval backend, but that does not erase the need for quality revalidation. Evidence: `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`, `2026-03-05-vector-db-quality-gate-qg1-closeout.md`.
15. Direct oMLX and the narrow `omlx-runtime` adapter looked stable; LiteLLM aliasing in front of oMLX did not. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`, `2026-04-27-omlx-runtime-phase3-validation.md`.
16. OpenHands is acceptable only as a local-bind managed service with operator access separated from runtime sandbox readiness. Evidence: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`.
17. Upstream MCP control-plane support does not imply usable client-session behavior. Evidence: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`.
18. Speech should stay behind a single facade; backend experiments are subordinate details. Evidence: `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md`, `2026-03-12-voice-gateway-xtts-runtime-proof-recovery.md`, `docs/foundation/topology.md`.
19. Monitoring and docs hygiene are part of runtime reliability, not separate process overhead. Evidence: `docs/journal/2026-02-09-prometheus-grafana-setup.md`, `2026-02-08-journal-integrity-policy.md`, `2026-04-02-root-allowlist-and-root-artifact-cleanup.md`.
20. Machine-checked manifests should outrank memory for repo hygiene and control-surface decisions. Evidence: `docs/journal/2026-04-02-homelab-durability-eval-loop.md`.

## 3. Top 15 V1 Keepers

1. One boring public gateway. Evidence: `README.md`, `docs/journal/2026-03-19-shared-8126-gpt-stack-canonicalized.md`.
2. Registry-driven runtime/gateway sync. Evidence: `docs/journal/2026-01-18-mlx-sync-gateway.md`, `2026-02-11-mlx-runtime-single-contract.md`.
3. LAN-first Mini↔Studio service traffic. Evidence: `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`, `docs/foundation/topology.md`.
4. Shared GPT runtime with explicit acceptance gates. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md`, `2026-03-19-public-deep-cutover-to-shared-8126.md`.
5. Specialized-runtime plane as a separate architectural boundary. Evidence: `docs/foundation/runtime-planes.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`.
6. Native OWUI+SearXNG+`safe_web` search path. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md`, `2026-05-01-searxng-reliability-hardening.md`.
7. Host-visible query-generation and retrieval-hygiene policy. Evidence: `docs/journal/2026-04-30-owui-querygen-prompt-policy.md`, `2026-04-30-websearch-quality-hardening.md`.
8. Source-scoped, redaction-first memory ingest with clean rollback. Evidence: `docs/journal/2026-03-04-codex-history-pilot-ingest.md`.
9. Memory API read/search vs write-token boundary. Evidence: `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`, `docs/INTEGRATIONS.md`.
10. Voice facade on Orin rather than direct client-to-backend speech coupling. Evidence: `docs/foundation/topology.md`, `docs/journal/2026-03-17-voice-gateway-control-plane-doc-hardening.md`.
11. Managed OpenHands with local bind and tailnet operator exposure only. Evidence: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`, `docs/foundation/topology.md`.
12. Localhost-only monitoring with repo-managed deployed config. Evidence: `docs/journal/2026-02-09-prometheus-grafana-setup.md`, `docs/INTEGRATIONS.md`.
13. Append-only journal discipline. Evidence: `docs/journal/README.md`, `docs/journal/2026-02-08-journal-integrity-policy.md`.
14. Narrow root control surface. Evidence: `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`, `README.md`.
15. Worktree-first mutable-work discipline for coding agents. Evidence: `AGENTS.md`, `docs/OPENCODE.md`.

## 4. Top 15 V1 Do-Not-Repeat Rules

1. Do not split boot/runtime authority. Evidence: `docs/journal/2026-02-11-mlx-runtime-single-contract.md`.
2. Do not leave shadow or rollout lanes half-retired. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`.
3. Do not treat tailnet transport as core runtime truth when LAN is stable. Evidence: `docs/journal/2026-03-16-lan-first-studio-gateway-contract-reset.md`.
4. Do not promote Qwen/vLLM constrained-tool behavior without hard proof. Evidence: `docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md`, `2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`.
5. Do not assume direct backend success implies gateway success. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`.
6. Do not revive custom web-search glue by default. Evidence: `docs/journal/2026-03-07-websearch-supported-path-reset.md`.
7. Do not confuse retrieval substrate health with retrieval-quality acceptance. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `2026-04-29-elastic-vector-db-cutover-runtime.md`.
8. Do not assume upstream MCP support is production-ready because registration/listing works. Evidence: `docs/journal/2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`.
9. Do not promote experimental systems to defaults before stable acceptance. Evidence: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `2026-04-15-qwen3-coder-next-failure-closeout.md`, `2026-04-21-omlx-litellm-shadow-alias-result.md`.
10. Do not make LiteLLM the long-term owner of provider formatting if the backend should own it. Evidence: `docs/journal/2026-04-22-gptoss-harmony-upstream-fix.md`.
11. Do not keep root clutter that competes with canon. Evidence: `docs/journal/2026-04-02-root-allowlist-and-root-artifact-cleanup.md`.
12. Do not claim XTTS or speech-backend readiness from import/CUDA proof alone. Evidence: `docs/journal/2026-03-12-voice-gateway-xtts-runtime-proof-recovery.md`.
13. Do not treat raw mirrors as automatic promotion oracles. Evidence: `docs/journal/2026-03-18-gpt-llmster-fast-observation-and-deep-usable-success-contract.md`, `docs/INTEGRATIONS.md`.
14. Do not make operator-only or experimental paths part of the canonical alias stack without explicit promotion. Evidence: `docs/journal/2026-03-19-shadow-ports-retired-and-docs-hardened.md`, `docs/INTEGRATIONS.md`.
15. Do not assume the current incumbent backend is the permanent V2 identity of the system. Evidence: `docs/journal/2026-02-18-mlx-runtime-backend-loop-and-revert.md`, `2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`.

## 5. Proposed Answers to the Open Questions

- Late-V1 GPT `llmster`: treat it as the latest accepted V1 compatibility baseline, not the V2 default. Evidence: `docs/journal/2026-03-19-public-deep-cutover-to-shared-8126.md`, `2026-03-19-shared-8126-gpt-stack-canonicalized.md`, `docs/foundation/runtime-planes.md`.
  Proposed answer: V2 should inherit the proven cutover discipline and the known-good GPT baseline, but should reselect its default backend through fresh evals. `llmster` is evidence, not destiny.

- Elastic retrieval: treat it as the incumbent candidate, not an unquestioned V2 law. Evidence: `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`, `2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `docs/v2/V1_LESSONS_LEARNED.md`.
  Proposed answer: V2 should keep the V1 retrieval discipline: source-scoped ingest, redaction-first handling, judged query packs, and quality gates. Elastic can be the starting incumbent, but backend choice should be revalidated with a slimmer V2 quality gate.

- Specialized-runtime plane: include the boundary immediately, not the required service immediately. Evidence: `docs/foundation/runtime-planes.md`, `docs/journal/2026-04-27-omlx-runtime-phase3-validation.md`, `docs/v2/V2_MIGRATION_NOTES.md`.
  Proposed answer: V2 architecture should include the specialized-runtime plane from day one, but phase-one runtime baseline should not require a concrete oMLX-style service unless it wins targeted evals for repeated-prefix, cache-sensitive, multi-sample, or coding-agent workloads.

## 6. Claims That Are Low-Confidence or Need Human/ChatGPT Review

- Any claim that OptiLLM should survive as a V2 default is low-confidence. Evidence is mixed and mostly canary/profile-specific: `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`.
- Any claim that Elastic should be V2 default without revalidation is low-confidence. Late-V1 proved runtime cutover, not final retrieval quality. Evidence: `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `2026-04-29-elastic-vector-db-cutover-runtime.md`.
- Any claim that oMLX should be publicly gateway-exposed is low-confidence. Direct and adapter evidence is good; LiteLLM alias evidence is negative. Evidence: `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`, `2026-04-27-omlx-runtime-phase3-validation.md`.
- Any claim that late-V1 Qwen work deserves preservation beyond historical reference is low-confidence. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`.
- Any claim that LiteLLM cleanup shims should be carried into V2 unchanged is low-confidence. Evidence: `docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md`, `2026-04-22-gptoss-harmony-upstream-fix.md`.
- Any claim that OpenHands should expand in V2 without fresh scope control is low-confidence. Managed service posture is proven; deeper shared tooling/model paths are not. Evidence: `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`, `2026-04-08-litellm-upstream-mcp-toolset-eval-no-go.md`.

## 7. Claims That Should Become V2 ADRs

- V2 keeps one boring public gateway and separates it from specialized runtime.
- V2 uses registry-driven runtime/gateway derivation; no split boot/runtime authority.
- V2 treats LAN-first Mini↔Studio service traffic as canonical; tailnet is operator access, not core runtime.
- V2 keeps native OWUI+SearXNG ownership boundaries for web search.
- V2 treats source-scoped, redaction-first ingest and delete-by-source rollback as mandatory retrieval discipline.
- V2 treats shadow/canary infrastructure as temporary and requires explicit retirement after cutover decisions.
- V2 keeps speech behind a single facade boundary.
- V2 keeps append-only journals and a narrow repo-root control surface.

Evidence: `docs/journal/2026-02-11-mlx-runtime-single-contract.md`, `2026-03-16-lan-first-studio-gateway-contract-reset.md`, `2026-03-07-websearch-supported-path-reset.md`, `2026-03-04-codex-history-pilot-ingest.md`, `2026-03-19-shadow-ports-retired-and-docs-hardened.md`, `2026-03-17-voice-gateway-control-plane-doc-hardening.md`, `2026-02-08-journal-integrity-policy.md`, `2026-04-02-root-allowlist-and-root-artifact-cleanup.md`.

## 8. Evidence Cards That Rely on Weak, Single-File, or Ambiguous Evidence

- EC-07 OptiLLM / inference-time compute is medium confidence and should stay medium. It compresses mixed evidence into a durable pattern, but the strongest direct evidence is still a small set of experimental entries. Evidence: `docs/v2/migration/EVIDENCE_CARDS.md`, `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`, `2026-03-06-plansearchtrio-reasoning-effort-synthesis.md`.
- EC-08 oMLX / specialized runtime is strong on “private portal” and weak on anything broader. The evidence is two files with one negative alias attempt and one successful narrow adapter validation. Evidence: `docs/v2/migration/EVIDENCE_CARDS.md`, `docs/journal/2026-04-21-omlx-litellm-shadow-alias-result.md`, `2026-04-27-omlx-runtime-phase3-validation.md`.
- EC-09 OpenHands / sandboxing is strong on managed local-bind posture and weak on future model/tooling depth. Evidence: `docs/v2/migration/EVIDENCE_CARDS.md`, `docs/journal/2026-03-31-openhands-managed-tailnet-service-promotion.md`.
- EC-12 Vector DB / retrieval is strong on discipline, weaker on backend finality. “Elastic primary” is late-V1 truth; “Elastic V2 default” is not yet earned. Evidence: `docs/v2/migration/EVIDENCE_CARDS.md`, `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`, `2026-04-29-elastic-vector-db-cutover-runtime.md`.
- EC-13 Orin voice / XTTS is strong on facade vs experiment distinction, but weak on any concrete future XTTS default. Evidence: `docs/v2/migration/EVIDENCE_CARDS.md`, `docs/journal/2026-03-12-voice-gateway-xtts-runtime-proof-recovery.md`, `2026-03-17-voice-gateway-control-plane-doc-hardening.md`.

## 9. Suggested Edits to the Six Seed Docs (Do Not Apply Yet)

- `docs/v2/migration/EVIDENCE_CARDS.md`
  - Add an explicit `Evidence strength` field or downgrade note for cards like EC-07, EC-08, EC-09, EC-12, EC-13.
  - Distinguish “accepted late-V1 baseline” from “candidate V2 default.”

- `docs/v2/V1_LESSONS_LEARNED.md`
  - Expand from 11 proven lessons to a cleaner top-20 list or explicitly say it is a compressed subset.
  - Fold the three open-question recommendations into the hypotheses section so the later packet is not the only place they are resolved.

- `docs/v2/V1_KEEPERS.md`
  - Split “keepers” into `accepted keepers` and `conditional keepers`.
  - Move any backend-identity language that sounds default-setting into a caution section.

- `docs/v2/V1_DO_NOT_REPEAT.md`
  - Add one line that some no-go items are permanent lessons while others are “re-test only if upstream/runtime evidence materially changes.”
  - Explicitly flag `main`, shadow-port, and some `boost-*` names as historical vocabulary likely not worth carrying into V2.

- `docs/v2/V2_MIGRATION_NOTES.md`
  - Replace the three open questions with the current recommended answers and move any remaining uncertainty to a short `review required` subsection.
  - Tighten wording so `llmster` reads as V1 accepted baseline, not implied V2 identity.

- `docs/v2/migration/JOURNAL_MAP.md`
  - Add a small `high-signal first` shortlist at the top for reviewers who do not want the full map.
  - Flag which mapped entries are superseded interpretation layers versus direct runtime or cutover records.

## Needs Human/ChatGPT Review

- Whether any V2 document should preserve the term `main` at all, given that current authoritative docs already retire it from the active LiteLLM alias surface. Evidence: `docs/INTEGRATIONS.md`, `docs/journal/2026-04-19-qwen-retirement-and-gpt-mlx-shadow-probe.md`.
- Whether `llmster` should be described in V2 as “fallback-compatible backend family” rather than by its current implementation name.
- Whether any OptiLLM profile survives as a named V2 concept, or whether only the general “late-stage extra reasoning, opt-in overlays” lesson should survive.
