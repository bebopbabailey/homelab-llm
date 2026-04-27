# Constraints: orchestration-cockpit

This service inherits global constraints from `../../AGENTS.md`.

## Hard constraints
- Keep this service localhost-only.
- Do not expose the cockpit publicly or via tailnet.
- Do not route ordinary chat to `omlx-runtime`.
- Do not add LiteLLM aliasing, Open WebUI integration, or OpenHands integration.
- Do not vendor the full Agent Chat UI source unless stock UI proves insufficient.
- Do not widen the specialized runtime contract beyond the frozen non-stream
  `/v1/chat/completions` shape already validated by `omlx-runtime`.

## Allowed operations
- Service-local Python graph, routing, and tests.
- Repo-owned UI wrapper docs and env examples only.
- Direct calls to the existing `omlx-runtime` client from Mini-side graph code.

## Forbidden operations
- New LAN exposure, host-binding changes, or public routing.
- MCP additions.
- LangGraph production deployment.
- Interrupt/human-approval flow.

## Validation pointers
- `uv run --project services/orchestration-cockpit python -m unittest discover -s services/orchestration-cockpit/tests -p 'test_*.py'`
- `uv run python scripts/service_registry_audit.py --strict --json`

## Change guardrail
If localhost ports, graph ID, or the ordinary/specialized route contract
change, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and the platform canon in the
same change.
