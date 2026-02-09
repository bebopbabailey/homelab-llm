# Autonomy Roadmap

## Purpose
Define a durable, phased path from chat-only operation to a safe, self-improving
local assistant platform. This document is strategic and long-lived.

## Scope
- Covers capability sequencing, guardrails, and graduation criteria.
- Complements (does not replace) operational truth docs:
  - `docs/PLATFORM_DOSSIER.md`
  - `docs/foundation/topology.md`
  - `docs/INTEGRATIONS.md`
  - `docs/foundation/testing.md`

## Non-goals
- Not a per-task implementation plan.
- Not a replacement for service-level `TASKS.md` files.
- Not a place for ephemeral scratch notes.

## Guiding principles
1. **Safety before autonomy**: policy checks and rollback paths are mandatory.
2. **Single front door**: clients route through LiteLLM by default.
3. **Small reversible steps**: each phase should deliver useful value.
4. **Source-of-truth discipline**: docs and config must remain aligned.

## Phased roadmap

### Phase A — Assistant Core (now)
Objective: stable chat gateway + reliable model routing + minimal drift.

Deliverables:
- Canonical docs aligned with active config/registry truth.
- Stable aliases and routing behavior validated.
- Baseline health + smoke checks documented and repeatable.

Graduation criteria:
- Core docs no longer conflict on ports/routing/auth/model handles.
- Verification commands succeed consistently.

### Phase B — Useful Tools (near-term)
Objective: move from chat-only to task-capable assistant.

Priority tools:
1. Home Assistant MCP (safe read + constrained write actions)
2. Web search + fetch + clean pipeline
3. Local notes/capture tool for durable task memory

Graduation criteria:
- At least 3 high-value workflows are executable end-to-end.
- Tool failures surface clear errors and recovery guidance.

### Phase C — Hot Memory / RAG (near-term)
Objective: operational memory over your own project artifacts.

Initial corpus:
- docs, runbooks, incident summaries, task outcomes, selected logs

Initial capability:
- Retrieve "what changed / what failed / how it was fixed"

Graduation criteria:
- Retrieval improves troubleshooting speed measurably.
- Memory ingestion and indexing are incremental and repeatable.

### Phase D — Voice Gateway (next)
Objective: speech interface over the same assistant core.

Approach:
- Keep existing model/tool stack as source of behavior.
- Add voice as another client/interface, not a parallel architecture.

Graduation criteria:
- Voice requests can execute the same workflows as chat.
- Latency and reliability are acceptable for daily use.

### Phase E — Expanded Autonomy (later)
Objective: bounded self-healing and selective self-updating loops.

Required controls:
- Risk tiers (read-only, docs-only, service-restart, privileged/system).
- Transactional execution: plan → diff → policy check → verify → rollback.
- Human approval gates for high-risk actions.

Graduation criteria:
- Autonomous loops resolve low-risk incidents without regressions.
- Escalation packets are complete when human intervention is required.

## Decision checkpoints
Use these checkpoints before promoting work between phases:
- Does this increase daily usefulness now?
- Does this reduce long-term complexity?
- Is it verifiable and rollback-safe?

If fewer than 2 answers are "yes", defer.

## Document relationships
- **Durable strategy**: this file (`autonomy-roadmap.md`)
- **Active execution**: `NOW.md`
- **Deferred work**: `BACKLOG.md`
- **Architecture decisions**: `docs/DECISIONS.md`
