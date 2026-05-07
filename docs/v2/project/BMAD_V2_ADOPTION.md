# V2 Planning Material: BMAD Adoption For The Seed Repo

Not current runtime truth. This file defines how BMAD should be used in the
next clean V2 repo without letting workflow artifacts replace core canon.

## Purpose

- Adopt BMAD as the primary planning and delivery workflow for V2.
- Keep the permanent repo canon smaller than the full set of planning and story
  artifacts produced during delivery.
- Make the handoff from strategy to implementation explicit for Codex and the
  human operator.

## BMAD Posture

- Adapt the new repo toward BMAD rather than treating BMAD as an optional
  wrapper.
- Use BMAD to structure planning, decomposition, and implementation handoff.
- Do not let every BMAD working artifact become permanent architecture truth.

## Stable Canon vs Workflow Artifacts

Permanent canon should stay in the seeded top-level docs:

- `VISION.md`
- `PRD.md`
- `ARCHITECTURE.md`
- contract docs such as gateway, RAG, evals, observability, and agent-lab
- ADRs

BMAD workflow artifacts should be treated as execution scaffolding:

- epics
- stories
- task decomposition
- implementation packets
- delivery checklists

BMAD project context is the bridge between the two.

## Recommended Mapping

- `VISION.md`
  - strategic identity and system boundaries
- `PRD.md`
  - BMAD product requirements anchor
- `ARCHITECTURE.md`
  - BMAD architecture anchor
- `docs/adr/`
  - durable rationale referenced by architecture and implementation
- BMAD `project-context`
  - compressed implementation constitution generated from the stable canon

## Workflow Order

Recommended sequence for the new repo:

1. lock the seed canon
2. extract doctrine and anti-patterns from V1
3. write or refine `VISION.md`, `PRD.md`, and `ARCHITECTURE.md`
4. generate or maintain BMAD project context from those docs
5. decompose into epics and stories
6. hand implementation to Codex using project context plus the relevant story

## Guardrails

- Do not let BMAD story artifacts redefine the public contract.
- Do not fork architecture truth between BMAD outputs and top-level canon.
- If a BMAD artifact discovers a real architecture change, land it back in the
  canon or ADRs first.
- Keep the generated project-context artifact grounded in current canon rather
  than V1 evidence packets.

## What BMAD Should Help Solve In V2

- better sequencing
- cleaner handoff from product intent to implementation
- modular decomposition without losing architecture cohesion
- repeatable agent execution with less prompt drift

## What BMAD Should Not Be Used To Justify

- premature service proliferation
- permanent duplication of the same requirements across many files
- replacing architecture docs with ephemeral planning output
- inheriting V1 structure just because it already exists
