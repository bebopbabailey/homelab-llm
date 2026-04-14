# Agent Guidance: Vector DB (Studio Main Store)

## Scope
- Studio-only main memory store for general retrieval over personal/export data.
- Postgres + pgvector, localhost-only bindings.

## Guardrails
- Do not expose new LAN ports without explicit plan + approval.
- Do not mix embedding spaces in one vector index.
- Keep Mini web-search pipeline out of scope for this service.
- Keep rollout shadow-first before coupling to production inference flows.

## Runtime ownership
- Studio launchd labels under `com.bebop.*` only.
- All owned labels must be allowlisted/audited by Studio scheduling policy.
