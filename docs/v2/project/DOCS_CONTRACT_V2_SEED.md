# V2 Planning Material: Seed `DOCS_CONTRACT`

Not current runtime truth. This file defines the documentation contract that
should seed the next clean V2 repo.

## Purpose

- Keep the new repo's canon small, explicit, and agent-friendly.
- Separate permanent truth from planning evidence and historical residue.
- Define when a bounded component must graduate into service-grade docs.

## Root Canon Contract

The repo root should contain only stable control-surface documents and operator
entrypoints.

Required top-level canon:

- `README.md`
- `VISION.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `GATEWAY_CONTRACT.md`
- `RAG_CONTRACT.md`
- `EVALS.md`
- `OBSERVABILITY.md`
- `AGENT_LAB.md`
- `DOCS_CONTRACT.md`

Allowed stable support surfaces:

- `AGENTS.md`
- repo config/control files that are truly live runtime or agent entrypoints
- BMAD-owned project-context output if the repo chooses to keep it near root;
  otherwise keep it in a dedicated BMAD output directory

Not allowed at root:

- dated reports
- migration packets
- host inventories
- one-off review packs
- implementation notes that are not active canon

## No Layer Taxonomy

- Do not create `layer-*` documentation trees in the new repo.
- Keep architecture planes in `ARCHITECTURE.md`.
- If navigation indexes are needed later, they should be secondary aids rather
  than contract surfaces.

## Component Promotion Rules

V2 should start with a few bounded components, not a formal service catalog.

A component stays documented by the root canon until it becomes one or more of
the following:

- a separately run process
- an externally consumed contract
- a risky execution boundary
- an independently validated runtime surface
- an operational unit with its own deployment or recovery steps

When a component crosses that threshold, promote it to service-grade docs.

## Staged Service-Grade Contract

Promotion starts with:

- `SERVICE_SPEC.md`

Add these only when justified by the component's maturity or risk:

- `RUNBOOK.md`
- `CONSTRAINTS.md`
- local `AGENTS.md`

Optional later additions:

- `ARCHITECTURE.md`
- `README.md`
- focused deep-dive docs

The rule is staged explicitness, not full ceremony everywhere from day one.

## ADR Contract

- Use `docs/adr/` for durable architecture and workflow decisions.
- Prefer short ADRs over one long rolling decision log.
- Use ADRs for decisions such as:
  - MLX-first posture
  - one public gateway
  - small stable alias set
  - staged component promotion
  - BMAD-as-primary workflow

## Evidence And History Contract

- Keep journal-style evidence outside the active canon.
- Preserve extracted evidence for confidence and traceability, but do not let
  it compete with the new repo's live contract.
- The new repo should not require reading historical packets to understand the
  intended system shape.

## Agent-Facing Contract

- The permanent canon must be sufficient for a coding agent to begin grounded
  implementation.
- BMAD planning artifacts should derive from the canon rather than becoming a
  second architecture truth surface.
- The agent-facing project-context artifact should compress the canon for
  implementation handoff, not replace it.

## Audit Heuristics For The New Repo

The seeded `DOCS_CONTRACT.md` should reject:

- root canon sprawl
- duplicated architecture truth across multiple competing docs
- service-grade doc bundles for components that are still just internal modules
- historical evidence presented as live contract
- navigation taxonomies pretending to be architecture truth
