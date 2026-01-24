# Gateway Layer

Mission: routing, auth, observability, and system monitoring. This is the only
entry point for client requests.

## Gateway handles registry
- Source of truth: `layer-gateway/registry/handles.jsonl`.
- A handle is registered if present; no health/state stored in the registry.
- Use `scripts/validate_handles.py` to validate schema + uniqueness.
- Naming: registry keys use `snake_case`; registry values use `kebab-case`.
- OptiLLM techniques are selected per-request via `optillm_approach`; handles stay stable.
  The older “route all MLX handles through OptiLLM” wiring is deprecated.
- Only models present on showroom machines (Mini/Studio) receive handles.
  Seagate storage is backroom-only and never exposed via LiteLLM.
- Deferred: endpoint and policy registries will be defined later.

## System monitor model (current)
- Monitor is **read‑only**: health checks + status queries.
- Monitor **does not restart services**; it escalates via a bulletin/DB entry.
- Overseer (root) or layer/service agents perform restarts and repairs.
- LLMs are only invoked after deterministic repairs fail.

## Planned
- Escalation bulletin stored in the system documentation DB (SQLite first).

See root docs: `/home/christopherbailey/homelab-llm/SYSTEM_OVERVIEW.md`.
Use `docs/` for deeper gateway notes.
