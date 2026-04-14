# Data Layer Dependencies

This layer owns registries and transitional taxonomy docs for Studio-local
persistence and memory services.

## Inbound
- Other layers read registries from this layer.
- Operators resolve the active memory-store service through `services/vector-db`.

## Outbound
- The active Studio-local vector-store service depends on policy-managed Studio
  launchd labels and local Postgres/pgvector runtime.

## Source-of-truth pointers
- `docs/_core/SOURCES_OF_TRUTH.md`
- `docs/_core/CHANGE_RULES.md`
