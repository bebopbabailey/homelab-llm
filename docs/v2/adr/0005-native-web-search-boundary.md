# ADR 0005: Native Web Search Boundary

V2 Planning Material. Not current runtime truth.

## Status

Proposed

## Context

V1 accumulated custom web-search glue, then deliberately deleted it and improved the native Open WebUI plus SearXNG path instead.

## Decision

V2 uses native OWUI + SearXNG + `safe_web` as the supported web-search path. Query-generation and retrieval-quality improvements belong at the UI/query/retrieval boundary before any new middleware is introduced.

## Consequences

- The supported path stays simpler and more discoverable.
- Search quality work is directed to the highest-signal boundary first.
- This blocks casual reintroduction of proxy/schema stacks without new evidence.

## V1 evidence

- `docs/journal/2026-03-07-websearch-supported-path-reset.md`
- `docs/journal/2026-04-30-owui-querygen-prompt-policy.md`
- `docs/journal/2026-05-01-searxng-reliability-hardening.md`

## V2 implications

V2 planning should treat custom search middleware as exceptional and require stronger justification than “native path needs tuning.”
