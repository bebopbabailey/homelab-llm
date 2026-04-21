# 2026-03-03 — Web-search rollout phase refresh (Mini-first cycle lock)

## Summary
- Refreshed the canonical web-search rollout phases to match current decisions.
- Locked this cycle to Mini-first web-search quality work through Phase 4D.
- Explicitly deferred Studio vector store work to a separate cycle/chat.

## Decisions codified
- Phase order for this cycle:
  1. Phase 2 closeout validation
  2. Phase 3 schema-first synthesis
  3. Phase 4A Mini-only vector assist
  4. Phase 4B TTL/retention policy
  5. Phase 4C keep Studio off synchronous search path
  6. Phase 4D end-to-end trace IDs
- Recommendation follow-ons (#3/#4/#5) remain in scope this cycle after 4A.
- Defaults locked for later implementation:
  - search chunk TTL: `48h`
  - compacted memory TTL: `14d`
  - trace contract: trace ID in logs + `/search` JSON response
  - Mini embedding default for 4A: `bge-small-en-v1.5`

## Scope guardrails
- No runtime behavior changes in this pass.
- No service restarts.
- No port/binding changes.
- No Studio vector tier implementation in this cycle.

## Files updated
- `BACKLOG.md`
- `NOW.md`
- `docs/foundation/testing.md`
- `docs/journal/index.md`

## Validation notes
- Documentation-only verification completed via targeted `rg`/`sed` checks.
- Canonical phase map now names Phase 4A/4B/4C/4D explicitly and includes
  out-of-scope statement for Studio vector work this cycle.
