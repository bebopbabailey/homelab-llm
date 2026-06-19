# Service Spec: omlx-agent-gateway

## Purpose
Provide a Mini-local, framework-neutral OpenAI-compatible URL for the Studio
oMLX Qwen3.6 agent backend primitive.

## Status
- Experimental
- Localhost-only sidecar on the Mini
- Not part of LiteLLM, Open WebUI, or OpenHands promotion

## Host & Runtime
- Host: Mini
- Bind: `127.0.0.1:4022`
- Upstream: Studio oMLX at `http://192.168.1.72:8120/v1`
- Public model id: `omlx-qwen36-27b-optiq-4bit`

## Endpoints
- `GET /health`
- `GET /v1/models`
- `GET /v1/model/info`
- `POST /v1/chat/completions`

## Contract
- Passes normal chat/tool requests to oMLX with only model-id normalization.
- Passes `stream=true` chat completions through to oMLX as server-sent events.
- Acts as an observability shim: propagates trace headers upstream, adds
  request/trace IDs to response headers, and records server/upstream spans when
  the local OpenTelemetry stack is available.
- Captures bounded local LLM prompt/response content for non-stream requests;
  streaming requests are metadata-only in this slice.
- Does not implement broad parser repair, LiteLLM behavior, MCP proxying, or
  OpenHands-specific policy.
- Optional local bearer auth is enabled by setting `OMLX_AGENT_GATEWAY_AUTH_TOKEN`
  in a local-only secret env file.

## Observability
- OTLP export target: `http://127.0.0.1:4318` through the shared
  `homelab-observability` package.
- Content cap: `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT=16384` and
  `HOMELAB_OTEL_CONTENT_ATTRIBUTE_LIMIT_BYTES=16384`.
- Export failure must not fail gateway requests.

## Non-Goals
- No LiteLLM alias.
- No public or LAN bind.
- No Open WebUI or OpenHands integration.
- No native MCP support in this slice.
