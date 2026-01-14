# Documentation Contract (Agent-Oriented)

This file defines the minimum documentation required at each directory level so
agents can operate safely within their sandbox.

## Root (monorepo) — “National manager” agent
Purpose: read-only orientation, safe diagnostics, and escalation routing.

Must include:
- **SYSTEM_OVERVIEW.md** — platform purpose and layer relationships
- **TOPOLOGY.md** — service map, ports, bindings, owners
- **CONSTRAINTS.md** — global non-negotiables (ports, gateway rule, LAN exposure)
- **INCIDENT_FLOW.md** — escalation rules and when to dispatch layer/service agents
- **DIAGNOSTICS.md** — safe read-only scripts and how to interpret output

## Layer (layer-*) — “Regional manager” agent
Purpose: define what the layer is allowed to do and its contracts.

Must include:
- **README.md** — layer mission + scope
- **CONSTRAINTS.md** — layer-specific non-negotiables
- **DEPENDENCIES.md** — contracts to adjacent layers (inputs/outputs)
- **RUNBOOK.md** — layer-level health checks and restart boundaries

## Service — “Shift lead” agent
Purpose: repair/deploy the service without touching others.

Must include:
- **README.md** — what it does + how to run
- **SERVICE_SPEC.md** — interface, ports, dependencies
- **ARCHITECTURE.md** — internal shape
- **AGENTS.md** — service-specific constraints + sandbox boundaries
- **RUNBOOK.md** — start/stop, logs, health, common failures
- **TASKS.md** — local TODOs
- `docs/README.md` — optional deep-dive entrypoint

## Notes
- Keep constraints short, explicit, and enforceable.
- Avoid duplicating global constraints in every service; reference root docs when possible.
- Prefer facts over aspirations. If a service is not active, say so explicitly.
