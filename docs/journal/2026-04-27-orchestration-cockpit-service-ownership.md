# 2026-04-27 orchestration-cockpit service ownership and observability

## Summary
Phase 5 promotes `orchestration-cockpit` from a working local prototype into a
repo-owned localhost-only Mini service boundary without changing the underlying
architecture.

The service remains:
- LangGraph code-first
- stock Agent Chat UI
- `omlx-runtime` as the specialized-runtime portal

What changed:
- service docs now describe a real Mini-owned localhost-only service target
- repo-managed target systemd units are defined for the graph and UI processes
- the graph now produces a small local JSONL run ledger
- specialized runs correlate one graph run to one `omlx-runtime` adapter
  `request_id`
- a Mermaid graph artifact is generated from the compiled graph and committed as
  a code-derived service artifact

## Scope
Kept out of scope:
- OpenHands
- MCP expansion
- LiteLLM aliasing
- Open WebUI changes
- public routing
- Langflow as canonical orchestration
- production LangGraph deployment
- custom cockpit UI

## Service shape
- Mini-owned
- localhost-only
- current runtime remains local/dev:
  - LangGraph Agent Server on `127.0.0.1:2024`
  - stock Agent Chat UI on `127.0.0.1:3030`
  - Mini `127.0.0.1:8129 -> Studio 127.0.0.1:8120` for specialized runtime

## Artifacts
- static Mermaid:
  - `services/orchestration-cockpit/docs/operator-cockpit.mmd`
- local run ledger:
  - `/tmp/orchestration-cockpit-phase5/run-ledger.jsonl`
- local correlated runtime telemetry:
  - `/tmp/orchestration-cockpit-phase5/omlx-runtime-telemetry.jsonl`

## Deferred
- standalone Agent Server / Docker production path
- non-dev persistence/runtime backing
- Agent Chat UI productionization
- Langflow visual-lab comparison work
