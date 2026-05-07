# V2 Planning Material: Session Types

Not current runtime truth. These are the allowed ChatGPT planning session types for the current V2 phase.

## Doctrine Review

- Objective: test whether V2 doctrine is clear, consistent, and evidence-backed.
- Allowed outputs: doctrine summaries, contradictions, wording cleanup recommendations.
- Forbidden outputs: infrastructure design, backend selection.
- Output posture: prefer `doctrine`, `historical reference`, and `unknown` labels where useful.
- Read first: [docs/v2/V1_KEEPERS.md](../V1_KEEPERS.md), [docs/v2/V1_DO_NOT_REPEAT.md](../V1_DO_NOT_REPEAT.md), [docs/v2/adr/](../adr/)

## Evidence Consolidation

- Objective: compress repeated lessons and separate proven claims from tentative ones.
- Allowed outputs: evidence-backed summaries, confidence notes, duplicate reduction suggestions.
- Forbidden outputs: promotion of candidates to defaults.
- Output posture: explicitly separate `doctrine`, `conditional candidate`, and `historical reference`.
- Read first: [docs/v2/migration/CHATGPT_REVIEW_PACKET.md](../migration/CHATGPT_REVIEW_PACKET.md), [docs/v2/migration/EVIDENCE_CARDS.md](../migration/EVIDENCE_CARDS.md)

## Inventory Reconciliation Review

- Objective: compare host inventories with canon and keep contradictions visible.
- Allowed outputs: blocker lists, unknown lists, reconciliation notes.
- Forbidden outputs: runtime cleanup plans or host mutation.
- Output posture: prefer `unknown` unless the repo already proves a stronger classification.
- Read first: [docs/v2/HOST_CANON_RECONCILIATION.md](../HOST_CANON_RECONCILIATION.md), [docs/v2/inventory/HOST_INVENTORY_SUMMARY.md](../inventory/HOST_INVENTORY_SUMMARY.md)

## Planning-Readiness Review

- Objective: decide whether the V2 docs are ready for the next docs-only planning slice.
- Allowed outputs: readiness checks, missing-prep lists, sequencing recommendations.
- Forbidden outputs: implementation plans for runtime services.
- Output posture: keep the result operational and checklist-driven.
- Read first: [docs/v2/PLANNING_READINESS_CHECKLIST.md](../PLANNING_READINESS_CHECKLIST.md), [docs/v2/README.md](../README.md)

## Open-Questions Triage

- Objective: separate true planning questions from questions the repo already answers.
- Allowed outputs: categorized open questions, evidence gaps, review-needed notes.
- Forbidden outputs: default selection by guesswork.
- Output posture: use `unknown` or `retest-only` rather than speculative decisions.
- Read first: [docs/v2/V1_LESSONS_LEARNED.md](../V1_LESSONS_LEARNED.md), [docs/v2/migration/CHATGPT_REVIEW_PACKET.md](../migration/CHATGPT_REVIEW_PACKET.md)

## Phase-Boundary Review

- Objective: confirm what is in scope for the current V2 planning phase and what is not yet allowed.
- Allowed outputs: phase-boundary summaries and guardrails.
- Forbidden outputs: expansion into LiteLLM, MLX, OpenHands, Orin, HP, or Home Assistant implementation planning.
- Output posture: keep “not yet” boundaries explicit.
- Read first: [docs/v2/README.md](../README.md), [docs/v2/PHASE_1A_PUBLIC_GATEWAY_SCOPE.md](../PHASE_1A_PUBLIC_GATEWAY_SCOPE.md)
