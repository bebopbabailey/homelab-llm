# 2026-05-26 OpenTelemetry cockpit slice

Objective: implement the first Mini-local OpenTelemetry trace path for
`orchestration-cockpit -> omlx-agent-gateway -> Studio oMLX`, while keeping
Prometheus metrics, model serving, LiteLLM aliases, Open WebUI, OpenHands, and
public exposure unchanged.

## Runtime shape

- Trace stack owner: `services/grafana`
- Collector: Grafana Alloy, package-managed, localhost-only OTLP:
  - `127.0.0.1:4317`
  - `127.0.0.1:4318`
- Trace backend: Tempo, package-managed, localhost-only query API:
  - `127.0.0.1:3200`
- Tempo retention: `48h`
- App helper package: `platform/observability-python`
- Tier 1 services:
  - `orchestration-cockpit`
  - `omlx-agent-gateway`

## Decisions

- `orchestration-cockpit` specialized requests now use the Mini-local
  `omlx-agent-gateway` sidecar instead of the older direct
  `OmlxRuntimeClient`/`127.0.0.1:8129` path.
- Gateway behavior remains passthrough plus observability shim: request IDs,
  trace propagation, server/upstream spans, and bounded local LLM content
  capture.
- Trace export is best-effort and local-only. Export failure must not fail app
  requests.
- Prompt/response content is captured only for local non-stream LLM requests
  and capped at `16 KiB` per attribute.
- The known Prometheus `*:9090` bind drift from the handoff is tracked but not
  fixed in this slice.

## Verification status

FULL verification passed on the Mini.

- Installed versions:
  - Alloy `1.16.1-1`
  - Tempo `2.10.5`
- Config validation:
  - `alloy validate services/grafana/config/alloy.river`
  - `tempo -config.file=services/grafana/config/tempo.yaml -target=all -config.verify=true`
- Unit tests:
  - `uv run --project services/orchestration-cockpit python -m unittest discover -s services/orchestration-cockpit/tests -p 'test_*.py'`
  - `uv run --project services/omlx-agent-gateway pytest services/omlx-agent-gateway/tests`
  - `uv run --project platform/observability-python pytest platform/observability-python/tests`
- Repo checks:
  - `uv run python scripts/worktree_effort.py preflight --stage verify --json`
  - `uv run python scripts/service_registry_audit.py --strict --json`
  - `uv run python scripts/repo_hygiene_audit.py --strict --scope root --json`
  - `uv run python scripts/repo_hygiene_audit.py --strict --scope journal --json`
  - `uv run python scripts/docs_link_audit.py`
- Runtime checks:
  - Grafana, Tempo, Alloy, cockpit graph, and gateway health checks passed.
  - `ss` showed trace stack listeners on localhost only for `4317`, `4318`,
    `14317`, `14318`, `3200`, and `12345`.
- Acceptance trace:
  - Trace ID: `419f0ce6546e233fca94ff5919f75dff`
  - Ledger run ID: `run-51d8035afc36`
  - Ledger adapter request ID: `adapter-367e2df88bc6`
  - Tempo trace contained `orchestration-cockpit` and `omlx-agent-gateway`
    service resources, `cockpit.specialized.invoke`, gateway FastAPI server
    spans, and `omlx_agent_gateway.upstream.chat`.
  - `gen_ai.request.messages` was present on cockpit and gateway upstream
    spans at the configured `16 KiB` cap.

Runtime notes:
- The package default Tempo attribute cap is `2048` bytes, so
  `services/grafana/config/tempo.yaml` sets `max_attribute_bytes: 16384` for
  this local-only stack.
- For verification before branch closeout, `orchestration-cockpit-graph` and
  `omlx-agent-gateway` were restarted against the linked worktree path.
