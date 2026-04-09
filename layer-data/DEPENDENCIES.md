# Data Layer Dependencies

This layer owns registries plus active Studio-local persistence and memory
services.

## Inbound
- Other layers read registries from this layer.

## Outbound
- Studio-local vector-store services depend on policy-managed Studio launchd
  labels and local Postgres/pgvector runtime.

## Source-of-truth pointers
- `docs/_core/SOURCES_OF_TRUTH.md`
- `docs/_core/CHANGE_RULES.md`
