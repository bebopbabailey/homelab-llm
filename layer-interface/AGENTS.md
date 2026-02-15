# Interface Layer (AGENTS)

Primary navigation: `docs/_core/README.md`.

## Scope
This layer contains human-facing UI and client entry points (e.g., Open WebUI,
Grafana, Voice Gateway).

## Non-negotiables
- Do not call inference backends directly. All model traffic goes through LiteLLM.
- Do not expose new LAN services without an explicit plan and approval.
- Do not commit secrets.
- When touching a service, read that service’s `AGENTS.md`, `CONSTRAINTS.md`, and `RUNBOOK.md` first.

## Adjacent layer contracts
See `layer-interface/DEPENDENCIES.md`.

