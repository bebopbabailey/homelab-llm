# V2 Planning Material: Seed Canon V2

Not current runtime truth. This file defines the permanent document set that
should seed the next clean V2 repo.

## Purpose

- Start the new repo from conclusions, not chronology.
- Give Codex and the human operator a small, durable canon that can drive BMAD
  planning and implementation handoff.
- Prevent the new repo from inheriting V1's documentation sprawl or taxonomy
  drift.

## Canon Principles

- Keep the permanent canon small.
- Put architecture and contract truth in top-level canonical docs.
- Promote per-component docs only when a component becomes operationally real
  enough to justify them.
- Keep journals, evidence packs, and migration notes outside the active canon.
- Use ADRs for decisions that need durable rationale.

## Initial Canon Set

- `README.md`
  - short repo orientation and navigation entrypoint
- `VISION.md`
  - what the system is and is not
- `PRD.md`
  - users, goals, scope, non-goals, success criteria
- `ARCHITECTURE.md`
  - planes, boundaries, runtime shape, deployment posture
- `GATEWAY_CONTRACT.md`
  - stable public APIs, alias policy, auth, health, model exposure rules
- `RAG_CONTRACT.md`
  - ingest, retrieval, citation, rollback, deletion-by-source rules
- `EVALS.md`
  - task families, score rules, promotion gates, benchmark hygiene
- `OBSERVABILITY.md`
  - metrics, traces, logs, run records, operator visibility rules
- `AGENT_LAB.md`
  - cockpit vs sandbox boundary, autonomy limits, execution safety
- `DOCS_CONTRACT.md`
  - promotion rules, doc ownership, and canon boundaries
- `docs/adr/`
  - short ADRs for durable architecture and workflow decisions
- BMAD project context artifact
  - agent-facing implementation constitution generated from the canon

## Canon Boundaries

The seed canon should answer these questions without needing journal replay:

- what the system is for
- what the first public contract must remain
- what architectural planes exist
- what retrieval and evaluation discipline are mandatory
- how agents may operate and where sandbox boundaries live
- when a bounded component must graduate into a service-grade doc set

The seed canon should not become:

- a migration diary
- a host inventory pack
- a backend benchmark scrapbook
- a service catalog before the system actually has independently operated
  services

## What To Extract From V1

- `doctrine`
  - stable decisions the new repo should inherit immediately
- `anti-patterns`
  - traps and retired ideas that should become explicit non-goals
- `evidence appendix`
  - supporting proof kept outside the active canon

## Evidence-Derived Defaults

- One boring public gateway remains the stable client-facing contract.
- MLX-first backend posture belongs in architecture rationale and ADRs, not in
  alias identity.
- Keep the initial alias set small and stable.
- Preserve plane separation between commodity inference, specialized runtime,
  orchestration, and execution boundary.
- Prefer staged promotion over service proliferation.

## Open Canon Questions For The Next Slice

- Whether phase one of the new repo should include a cockpit baseline or stop
  at gateway-first assistant infrastructure.
- Whether a task or job API belongs in the first canon or should stay outside
  phase one.
- Which BMAD-generated artifact path should be treated as the authoritative
  project-context output in the new repo.
