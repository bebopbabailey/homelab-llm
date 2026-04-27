# Architecture: orchestration-cockpit

## Purpose
`orchestration-cockpit` is a Mini-owned localhost-only cockpit service for the
orchestration plane. It preserves the working phase-4 browser flow while giving
the repo a real local service boundary around:
- a LangGraph code-first orchestration graph
- a stock Agent Chat UI operator surface
- a narrow specialized-runtime dependency on `omlx-runtime`
- minimal generated observability owned by the service itself

## Current local posture
- Mini-local only.
- LangGraph Agent Server in local/dev mode on `127.0.0.1:2024`.
- Agent Chat UI on `127.0.0.1:3030`.
- No public routing, no Open WebUI integration, no LiteLLM aliasing.
- Agent Chat UI source stays outside the repo; this service owns only
  connection docs, env wrappers, and service wrappers.
- The specialized-runtime path stays:
  - Mini `127.0.0.1:8129`
  - SSH forward
  - Studio `127.0.0.1:8120`
- Phase 6 makes the graph and UI normal localhost-only `systemd` services while
  keeping the specialized forward external.

## Graph boundary
- Graph ID: `operator-cockpit`
- The graph uses a deterministic command syntax:
  - `/specialized <fixture-id> ...` routes to `omlx-runtime`
  - everything else stays on the ordinary placeholder path
- The ordinary path is deliberately non-LLM-backed in this phase.
- The specialized path uses the existing `OmlxRuntimeClient` without semantic
  rewriting, fallback logic, or provider normalization.

## Service-owned observability
- Static visualization comes from the compiled graph itself.
- Canonical static artifact:
  - `services/orchestration-cockpit/docs/operator-cockpit.mmd`
- Runtime correlation stays local:
  - graph run ledger under `~/.local/state/orchestration-cockpit/`
  - `omlx-runtime` adapter telemetry under the same artifact root
- The service does not build a custom dashboard in this phase.

## Local service ownership target
- Graph unit target:
  - `orchestration-cockpit-graph.service`
- UI unit target:
  - `orchestration-cockpit-ui.service`
- These units define the repo-owned local launch shape.
- Phase 6 validates them as disabled-by-default localhost-only services; it does
  not turn them into a production deployment contract.

## LangSmith posture
- Agent Chat UI does not require a LangSmith key for local server use.
- `langgraph dev` may still require a local LangSmith API key as a tooling
  prerequisite.
- If a key is required, it is local-only, uncommitted, not part of cockpit
  auth, and not a LangSmith UI dependency.

## Later production-shaped path
Later, this service can move from the local/dev Agent Server posture to a more
production-shaped runtime:
- LangGraph standalone Agent Server / Docker image
- non-dev persistence/runtime backing such as Redis/Postgres or the then-current
  LangGraph deployment requirements
- a productionized UI hosting path only after the local service contract proves
  durable

That path is documented here to keep the service shape honest, but it is
explicitly deferred in phase 6.

## Langflow posture
Langflow is a later workflow-lab comparison candidate only.
- It is not the source of truth for orchestration.
- It is not part of this service implementation.
- It is not allowed to create a second workflow definition in phase 6.

## Non-goals
- Public operator surface
- Broad assistant behavior
- Interrupts or approval flows
- Commodity-model quality evaluation
- Generalized OpenAI compatibility for `omlx-runtime`
- Custom cockpit UI
- Production deployment
