# omlx-runtime fixtures

This directory holds the frozen phase-3 fixture specifications used by the
specialized runtime-plane adapter and its direct-vs-adapter runtime proof.

The fixture family stays centered on the direct workload classes already
validated in the
experimental journals:
- `S01`
- `S02`
- `S03`
- `S04`
- smoke
- 4k long-context guardrail

`phase3_fixture_specs.json` is intentionally narrow:
- non-stream `/v1/chat/completions` only
- two-message `system` + `user` payloads only
- deterministic repeated-prefix pseudo-repository context
- concurrency classes `c1` and `c2` only

The adapter must preserve those shapes rather than inventing a broader generic
compatibility layer.
