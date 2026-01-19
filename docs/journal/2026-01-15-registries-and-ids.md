# 2026-01-15 — Registries, Entity IDs, and JSONL Plan

## Summary
We clarified how the gateway should treat aliases and how to structure registry data
for an eventual SQLite system documentation DB.

## Key decisions / direction
- **Alias is a routing selector** for the gateway (one `model` key per request).
- **Alias is not the global primary key** for the whole system, but it *is* the
  primary key for the **gateway registry**.
- **Entities are not only models**: tools and services also need registry entries.
- The DB should be **entity‑centric**, with aliases as attributes.

## Proposed entities (draft)
- `model` (model backends)
- `tool` (MCP tools)
- `service` (runtime services)
- `alias` (gateway routing aliases)
- `workflow` (later, if needed)

## JSONL now, DB later
We agreed to create **JSONL registries per layer** as a bridge to the future DB.
JSONL maps cleanly to DB rows and is easy to import later.

## Gateway registry focus
- Gateway should be **model‑centric** at the alias layer.
- A single gateway endpoint serves many aliases, so alias registry is the core.
- Ports and downstream endpoints are still needed for monitoring and routing.

## Next steps (planned)
- Create per‑layer JSONL registries under `layer-*/docs/`.
- Include a gateway alias registry and a gateway endpoint list.
- Later: import JSONL into SQLite and replace docs with DB exports.
