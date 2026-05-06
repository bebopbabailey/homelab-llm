# ADR 0006: Retrieval Discipline Before Backend Default

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 proved that backend bring-up and retrieval quality are different gates, and that disciplined ingest mattered more than the first chosen storage engine.

## Decision

V2 treats source-scoped ingest, redaction-first handling, delete-by-source rollback, judged eval packs, and explicit quality gates as doctrine. Elastic is only the incumbent candidate, not the unquestioned V2 default.

## Consequences

- Retrieval quality has to be earned instead of assumed from backend stability.
- Memory ingest remains reversible and source-bounded.
- Backend swaps remain possible without abandoning the doctrine.

## V1 evidence

- `docs/journal/2026-03-04-codex-history-pilot-ingest.md`
- `docs/journal/2026-03-05-vector-db-quality-gate-qg1-closeout.md`
- `docs/journal/2026-04-29-elastic-vector-db-cutover-runtime.md`

## V2 implications

V2 planning should specify retrieval discipline first and defer backend finality until the incumbent passes a slimmer V2 quality gate.
