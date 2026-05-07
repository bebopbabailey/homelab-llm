# V2 Planning Material: Project Source Guide

Not current runtime truth. This guide tells planning sessions which sources to trust and how to classify them.

## Source Precedence For Planning

1. Active runtime canon for current truth
2. `docs/v2/*` for planning synthesis
3. `docs/journal/*` as evidence only

## Doctrine Sources

- [docs/v2/V1_KEEPERS.md](../V1_KEEPERS.md)
- [docs/v2/V1_DO_NOT_REPEAT.md](../V1_DO_NOT_REPEAT.md)
- [docs/v2/V2_MIGRATION_NOTES.md](../V2_MIGRATION_NOTES.md)
- [docs/v2/adr/](../adr/)

Use these when classifying `doctrine`.

## Migration Synthesis Sources

- [docs/v2/migration/CHATGPT_REVIEW_PACKET.md](../migration/CHATGPT_REVIEW_PACKET.md)
- [docs/v2/migration/EVIDENCE_CARDS.md](../migration/EVIDENCE_CARDS.md)
- [docs/v2/migration/JOURNAL_MAP.md](../migration/JOURNAL_MAP.md)
- [docs/v2/V1_LESSONS_LEARNED.md](../V1_LESSONS_LEARNED.md)

Use these when classifying `conditional candidate`, `historical reference`, or `retest-only`.

## Inventory Sources

- [docs/v2/inventory/HOST_INVENTORY_SUMMARY.md](../inventory/HOST_INVENTORY_SUMMARY.md)
- [docs/v2/inventory/MINI_BASELINE.md](../inventory/MINI_BASELINE.md)
- [docs/v2/inventory/STUDIO_BASELINE.md](../inventory/STUDIO_BASELINE.md)
- [docs/v2/inventory/ORIN_BASELINE_PENDING.md](../inventory/ORIN_BASELINE_PENDING.md)
- [docs/v2/inventory/HP_BASELINE_PENDING.md](../inventory/HP_BASELINE_PENDING.md)

Use these when classifying `unknown` or pending evidence.

## Category Mapping

- `doctrine`: V2 ADRs, `V1_KEEPERS`, `V1_DO_NOT_REPEAT`, resolved migration notes
- `conditional candidate`: evidence cards, review packet, late-V1 accepted but not promoted systems
- `historical reference`: retired lanes, old aliases, no-go branches
- `retest-only`: items explicitly marked for retest if upstream/runtime conditions change
- `unknown`: host/canon contradictions, pending inventories, weak evidence
