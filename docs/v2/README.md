# V2 Planning Material

Not current runtime truth. V2 docs remain planning material unless a document is explicitly promoted into canon.

Current runtime truth remains the active platform, topology, integration, and per-service docs:

- [docs/PLATFORM_DOSSIER.md](../PLATFORM_DOSSIER.md)
- [docs/foundation/topology.md](../foundation/topology.md)
- [docs/INTEGRATIONS.md](../INTEGRATIONS.md)
- `platform/registry/services.jsonl` plus each active service's `SERVICE_SPEC.md`, `RUNBOOK.md`, and `CONSTRAINTS.md`

## Current V2 Phase

- Phase: planning synthesis, inventory reconciliation, and seed-canon definition.
- Goal: define the V2 command center, preserve the proven public contract, separate preserve-now evidence from rebuild-clean candidates, and lock the first clean-repo documentation constitution.
- Inputs are now grounded across Mini, Studio, Orin, HP, and the HAOS VM, with stronger detail still concentrated on Mini and Studio.
- V2 doctrine is set at the contract level first: one public gateway, private specialized runtimes until eval-proven, registry-derived routing, LAN-first service traffic, and retrieval discipline before backend finality.

## Recommended Reading Order

1. [README.md](../../README.md)
2. [docs/_core/SOURCES_OF_TRUTH.md](../_core/SOURCES_OF_TRUTH.md)
3. [docs/PLATFORM_DOSSIER.md](../PLATFORM_DOSSIER.md)
4. [docs/foundation/topology.md](../foundation/topology.md)
5. [docs/INTEGRATIONS.md](../INTEGRATIONS.md)
6. [docs/v2/V2_MIGRATION_NOTES.md](V2_MIGRATION_NOTES.md)
7. [docs/v2/V1_KEEPERS.md](V1_KEEPERS.md)
8. [docs/v2/V1_DO_NOT_REPEAT.md](V1_DO_NOT_REPEAT.md)
9. [docs/v2/adr/](adr/)
10. [docs/v2/inventory/HOST_INVENTORY_SUMMARY.md](inventory/HOST_INVENTORY_SUMMARY.md)
11. [docs/v2/REBUILD_CUTOVER_MAP.md](REBUILD_CUTOVER_MAP.md)

## Not Yet

- No LiteLLM rebuild yet.
- No MLX runtime rebuild yet.
- No OpenHands expansion yet.
- No Orin integration work yet.
- No HP integration work yet.
- No deletion or stop actions yet.

## V2 Planning Set

### Migration synthesis

- [docs/v2/V1_LESSONS_LEARNED.md](V1_LESSONS_LEARNED.md)
- [docs/v2/V1_KEEPERS.md](V1_KEEPERS.md)
- [docs/v2/V1_DO_NOT_REPEAT.md](V1_DO_NOT_REPEAT.md)
- [docs/v2/V2_MIGRATION_NOTES.md](V2_MIGRATION_NOTES.md)
- [docs/v2/migration/CHATGPT_REVIEW_PACKET.md](migration/CHATGPT_REVIEW_PACKET.md)
- [docs/v2/migration/EVIDENCE_CARDS.md](migration/EVIDENCE_CARDS.md)
- [docs/v2/migration/JOURNAL_MAP.md](migration/JOURNAL_MAP.md)

### ADRs

- [docs/v2/adr/0001-one-public-gateway.md](adr/0001-one-public-gateway.md)
- [docs/v2/adr/0002-runtime-plane-separation.md](adr/0002-runtime-plane-separation.md)
- [docs/v2/adr/0003-registry-derived-routing.md](adr/0003-registry-derived-routing.md)
- [docs/v2/adr/0004-lan-first-service-traffic.md](adr/0004-lan-first-service-traffic.md)
- [docs/v2/adr/0005-native-web-search-boundary.md](adr/0005-native-web-search-boundary.md)
- [docs/v2/adr/0006-retrieval-discipline-before-backend-default.md](adr/0006-retrieval-discipline-before-backend-default.md)
- [docs/v2/adr/0007-shadow-infrastructure-retirement.md](adr/0007-shadow-infrastructure-retirement.md)
- [docs/v2/adr/0008-speech-facade-boundary.md](adr/0008-speech-facade-boundary.md)
- [docs/v2/adr/0009-agent-worktree-discipline.md](adr/0009-agent-worktree-discipline.md)

### Host inventory

- [docs/v2/inventory/HOST_INVENTORY_SUMMARY.md](inventory/HOST_INVENTORY_SUMMARY.md)
- [docs/v2/inventory/NODE_QUICK_REFERENCE.md](inventory/NODE_QUICK_REFERENCE.md)
- [docs/v2/inventory/MINI_BASELINE.md](inventory/MINI_BASELINE.md)
- [docs/v2/inventory/STUDIO_BASELINE.md](inventory/STUDIO_BASELINE.md)
- [docs/v2/inventory/ORIN_BASELINE.md](inventory/ORIN_BASELINE.md)
- [docs/v2/inventory/HP_BASELINE.md](inventory/HP_BASELINE.md)
- [docs/v2/inventory/HAOS_BASELINE.md](inventory/HAOS_BASELINE.md)

### Rebuild planning

- [docs/v2/REBUILD_CUTOVER_MAP.md](REBUILD_CUTOVER_MAP.md)

### Planning prep

- [docs/v2/PLANNING_READINESS_CHECKLIST.md](PLANNING_READINESS_CHECKLIST.md)

### Project prep

- [docs/v2/project/CHATGPT_PROJECT_SEED.md](project/CHATGPT_PROJECT_SEED.md)
- [docs/v2/project/PROJECT_INSTRUCTIONS.md](project/PROJECT_INSTRUCTIONS.md)
- [docs/v2/project/PROJECT_SOURCE_GUIDE.md](project/PROJECT_SOURCE_GUIDE.md)
- [docs/v2/project/SESSION_TYPES.md](project/SESSION_TYPES.md)
- [docs/v2/project/SEED_CANON_V2.md](project/SEED_CANON_V2.md)
- [docs/v2/project/DOCS_CONTRACT_V2_SEED.md](project/DOCS_CONTRACT_V2_SEED.md)
- [docs/v2/project/BMAD_V2_ADOPTION.md](project/BMAD_V2_ADOPTION.md)

### Agent prep

- [docs/v2/agent/CODEX_PLANNING_BRIEF.md](agent/CODEX_PLANNING_BRIEF.md)
- [docs/v2/agent/CODEX_PROMPT_TEMPLATE.md](agent/CODEX_PROMPT_TEMPLATE.md)
- [docs/v2/agent/CODEX_DEBRIEF_TEMPLATE.md](agent/CODEX_DEBRIEF_TEMPLATE.md)
- [docs/v2/agent/EVIDENCE_USE_POLICY.md](agent/EVIDENCE_USE_POLICY.md)

## Working Rules For Future Sessions

- Treat baseline inventories as evidence snapshots, not self-updating truth.
- If Mini or Studio inventory and current canon disagree, record the mismatch before assuming one is correct.
- Keep backend names as implementation detail unless a V2 doc explicitly promotes them.
- Keep specialized runtime surfaces private until they win explicit evals and promotion.
