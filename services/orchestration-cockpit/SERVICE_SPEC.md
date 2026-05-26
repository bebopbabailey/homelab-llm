# Service Spec: orchestration-cockpit

## Purpose
Represent a repo-owned Mini-local cockpit service for the orchestration plane.

## Status
- Experimental
- Mini-owned localhost-only runtime
- Local/dev Agent Server posture only
- No production deployment in this phase
- No public route
- systemd-owned local service target in phase 6

## Host & ownership
- Owner host: Mini
- Plane: orchestration
- Service kind: UI/orchestration local service

## Runtime shape
- Current runtime:
  - LangGraph local/dev Agent Server under a repo-managed systemd unit
  - stock Agent Chat UI from an external scaffold or local checkout under a
    repo-managed systemd unit
  - repo-owned wrappers, tracked `langgraph.json`, env templates, runbook,
    generated Mermaid, and local artifacts
- Later production-shaped path is documented but deferred:
  - LangGraph standalone Agent Server / Docker image
  - non-dev persistence/runtime backing
  - productionized UI hosting only later

## Local topology
- LangGraph Agent Server: `127.0.0.1:2024`
- Agent Chat UI: `127.0.0.1:3030`
- Specialized runtime forward: `127.0.0.1:8129 -> Studio 127.0.0.1:8120`
- Graph ID: `operator-cockpit`

## Ingress posture
- Browser GUI is localhost-only.
- Agent Chat UI connects to the local LangGraph Agent Server by graph ID.
- The service does not expose a public gateway contract and does not replace
  LiteLLM.

## Local service ownership target
- Repo-managed unit target:
  - `platform/ops/systemd/orchestration-cockpit-graph.service`
- Repo-managed unit target:
  - `platform/ops/systemd/orchestration-cockpit-ui.service`
- Installed host env files:
  - `/etc/orchestration-cockpit/graph.env`
  - optional `/etc/orchestration-cockpit/graph.secret.env`
  - `/etc/orchestration-cockpit/ui.env`
- Supported host-owned paths:
  - Agent Chat UI root:
    - `/home/christopherbailey/.local/share/orchestration-cockpit/agent-chat-ui`
  - runtime state/artifacts:
    - `/home/christopherbailey/.local/state/orchestration-cockpit`
- Phase 6 installs and validates the units, but does not enable them on boot.

## Mission contract
- Required graph state includes:
  - `messages`
  - `thread_id`
  - `run_id`
  - `started_at`
  - `mission_mode`
  - `route_decision`
  - `route_reason`
  - `fixture_id`
  - `node_sequence`
  - `adapter_request_id`
  - `specialized_payload`
  - `specialized_result`
  - `pi_task`
  - `pi_temperature`
  - `pi_max_tokens`
  - `pi_command`
  - `pi_result`
  - `final_text`
  - `error`
- Deterministic route syntax:
  - `/specialized <fixture-id> <freeform mission text>`
  - `/pi <freeform scratch coding task>`
  - `/pi --temperature <0..2> --max-tokens <256..16384> <task>` for the two
    supported request knobs
- Valid specialized fixture IDs:
  - `G01`
  - `G02`
  - `S01`
  - `S02`
  - `S03`
  - `S04`

## Ordinary path
- Deterministic placeholder only in this phase
- No LiteLLM call
- No commodity-model evaluation

## Pi scratch-run path
- Uses the existing stable Pi/Qwen playground launcher:
  `/home/christopherbailey/pi-qwen-trials/current/run_pi_qwen.py`.
- Requires the Mini-local oMLX Qwen sidecar at `127.0.0.1:4022`.
- Scratch-only: the launcher creates disposable repos under
  `/home/christopherbailey/pi-qwen-trials/current/runs/<run-id>/`.
- The cockpit launches Pi synchronously and returns a summary plus artifact
  paths for the manifest, transcript JSONL, final diff, and final test log.
- The cockpit ledger stores pointers to Pi artifacts; it does not copy or
  rewrite Pi run output.
- Model, provider, and validation command remain fixed by the launcher in this
  slice.

## Specialized path
- Uses the Mini-local `omlx-agent-gateway` OpenAI-compatible sidecar so traces
  can correlate cockpit graph spans with gateway upstream spans.
- Requires:
  - `OMLX_AGENT_GATEWAY_BASE_URL`
  - `OMLX_AGENT_GATEWAY_MODEL_ID`
  - optional `OMLX_AGENT_GATEWAY_AUTH_TOKEN`
- Preserves the frozen non-stream request shape:
  - `POST /v1/chat/completions`
  - non-stream only
  - exact keys: `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stream`
  - exactly two messages: `system`, then `user`
  - plain string `content` only
- Specialized runs must correlate one graph `run_id` to one
  `adapter_request_id` and one OpenTelemetry `trace_id`.

## Tooling preflight
- Agent Chat UI itself does not require a LangSmith key for local server use.
- `langgraph dev` may still require `LANGSMITH_API_KEY`.
- If required, the key is:
  - local-only
  - not committed
  - not part of cockpit auth
  - not a LangSmith UI dependency
- Safari access to hosted LangSmith Studio uses the LangGraph dev server
  tunnel option, controlled by `ORCHESTRATION_COCKPIT_GRAPH_TUNNEL=true`.

## Local observability
- Canonical static graph artifact: generated Mermaid from the compiled graph
- Canonical runtime artifact: small local JSONL run ledger
- OpenTelemetry traces export to the Mini-local Alloy listener at
  `127.0.0.1:4318` when runtime env is installed.
- Specialized ledger rows include `trace_id`.
- Local LLM prompt/response content may be captured in traces with the shared
  `homelab-observability` 16 KiB attribute cap.
- Default artifact root:
  `/home/christopherbailey/.local/state/orchestration-cockpit`
- No cloud observability dependency is required.

## Runtime hygiene
- Repo-local `.env` is for manual local use only and is not the service runtime
  authority.
- The tracked `langgraph.json` remains the config source of truth.
- The live runtime `langgraph.json` copy under
  `~/.local/state/orchestration-cockpit/langgraph-runtime/` is generated from
  repo truth only and must not be edited by hand.
- `uv.lock` is committed for reproducibility and is not a disposable runtime
  artifact.

## Explicit non-goals
- Public routing
- Open WebUI integration
- LiteLLM aliasing
- OpenHands integration
- MCP expansion
- Custom cockpit React UI
- Langflow as a second workflow source of truth
- Production LangGraph deployment in this phase
