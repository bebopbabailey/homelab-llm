# Data Layer

Mission: persistence and memory (vector DB, summaries, registries) that supports
the rest of the system.

Transitional status:
- `layer-data/` is now a taxonomy and registry surface, not a live service root.
- The active vector-store service root is `services/vector-db`.

See root docs: `/home/christopherbailey/homelab-llm/SYSTEM_OVERVIEW.md`.
Use `docs/` for deeper data notes.

## Registries
- Lexicon registry: `layer-data/registry/lexicon.jsonl` (deterministic term correction)
