# V2 Planning Material: ChatGPT Project Seed

Not current runtime truth. This file seeds a ChatGPT Project for V2 planning only.

## Purpose

- Create a bounded planning workspace for reviewing V2 evidence and doctrine.
- Help ChatGPT stay inside V2 planning prep instead of drifting into infrastructure design.

## This Project Is For

- doctrine review
- evidence consolidation
- inventory reconciliation review
- planning-readiness review
- open-questions triage

## This Project Is Not For

- V2 infrastructure design
- backend or model selection
- repo-layout decisions
- runtime implementation planning
- BMAD workflow planning

## Read First

1. [docs/v2/README.md](../README.md)
2. [docs/v2/V2_MIGRATION_NOTES.md](../V2_MIGRATION_NOTES.md)
3. [docs/v2/V1_KEEPERS.md](../V1_KEEPERS.md)
4. [docs/v2/V1_DO_NOT_REPEAT.md](../V1_DO_NOT_REPEAT.md)
5. [docs/v2/migration/CHATGPT_REVIEW_PACKET.md](../migration/CHATGPT_REVIEW_PACKET.md)
6. [docs/v2/inventory/HOST_INVENTORY_SUMMARY.md](../inventory/HOST_INVENTORY_SUMMARY.md)
7. [docs/v2/adr/0001-one-public-gateway.md](../adr/0001-one-public-gateway.md)
8. [docs/v2/adr/0009-agent-worktree-discipline.md](../adr/0009-agent-worktree-discipline.md)

## Evidence Categories

- `doctrine`
- `conditional candidate`
- `historical reference`
- `retest-only`
- `unknown`

## Required Posture

- Keep current runtime truth separate from V2 planning material.
- Back every major claim with repo evidence.
- If evidence is mixed or missing, mark the conclusion `unknown`.
- Treat candidates as candidates, not defaults.
- Prefer planning-prep and evidence-review sessions before broader V2 planning slices.

## Prohibited Moves

- choosing V2 backends
- choosing V2 repo layout
- promoting candidates to defaults
- proposing service mutation
- introducing BMAD-specific planning
