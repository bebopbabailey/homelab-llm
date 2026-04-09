# Documentation Contract (Agent-Oriented)

This file defines the minimum documentation required at each directory level so
agents can operate safely within their sandbox.

## Sources of truth
Resolve cross-document conflicts using `docs/_core/SOURCES_OF_TRUTH.md`.

## Root (monorepo) — “National manager” agent
Purpose: read-only orientation, safe diagnostics, and escalation routing.

Must include:
- **SYSTEM_OVERVIEW.md** — platform purpose and layer relationships
- **TOPOLOGY.md** — service map, ports, bindings, owners
- **CONSTRAINTS.md** — global non-negotiables (ports, gateway rule, LAN exposure)
- **INCIDENT_FLOW.md** — escalation rules and when to dispatch layer/service agents
- **DIAGNOSTICS.md** — safe read-only scripts and how to interpret output

Allowed repo-root files:
- `.gitignore`
- `.gitmodules`
- `AGENTS.md`
- `README.md`
- `DOCS_CONTRACT.md`
- `CONSTRAINTS.md`
- `SYSTEM_OVERVIEW.md`
- `TOPOLOGY.md`
- `DIAGNOSTICS.md`
- `INCIDENT_FLOW.md`
- `SANDBOX_PERMISSIONS.md`
- `NOW.md`
- `BACKLOG.md`
- `SCRATCH_PAD.md`
- `opencode.json`

Placement rules:
- root: stable monorepo orientation and live control files only
- `docs/journal/`: dated narrative, closeouts, and decisions
- `docs/archive/`: rollup-oriented historical archive surface only
- `next-projects/`: future-looking plans that are not root canon
- layer/service docs: active operational truth for a specific boundary
- canonical enforcement manifest: `docs/_core/root_hygiene_manifest.json`
- enforced by `scripts/repo_hygiene_audit.py`

## Layer (layer-*) — “Regional manager” agent
Purpose: define what the layer is allowed to do and its contracts.

Must include:
- **README.md** — layer mission + scope
- **AGENTS.md** — thin layer entrypoint + descent guidance
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
- **CONSTRAINTS.md** — service-specific non-negotiables
- **RUNBOOK.md** — start/stop, logs, health, common failures
- **TASKS.md** — local TODOs
- `docs/README.md` — optional deep-dive entrypoint

## Notes
- Read order for edits should descend from root to layer to service.
- If touched files are below the service root, read every `AGENTS.md` on the path
  from the service root to the touched directory, with the deepest applicable
  file treated as the most specific guidance.
- Registry/data directories under `layer-*/registry` are not service directories by default.
- Service-level documentation requirements apply only to directories that expose an actual service contract.
- Data registries may document themselves, but they are not audited as services unless intentionally promoted to service status.
- Keep constraints short, explicit, and enforceable.
- Avoid duplicating global constraints in every service; reference root docs when possible.
- Prefer facts over aspirations. If a service is not active, say so explicitly.
- If this contract conflicts with root constraints or source hierarchy, update this file to align with canon.
- Do not leave dated reports, review packs, or speculative design packets at
  repo root once their durable home is known.
- Do not leave one-file-per-packet historical copies at the top level of
  `docs/archive/`; use dated rollups there and quarantine legacy leftovers
  under `docs/archive/legacy/` during migration.
