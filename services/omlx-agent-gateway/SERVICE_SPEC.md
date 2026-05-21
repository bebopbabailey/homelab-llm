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
- Does not implement broad parser repair, LiteLLM behavior, MCP proxying, or
  OpenHands-specific policy.
- Optional local bearer auth is enabled by setting `OMLX_AGENT_GATEWAY_AUTH_TOKEN`
  in a local-only secret env file.

## Non-Goals
- No LiteLLM alias.
- No public or LAN bind.
- No Open WebUI or OpenHands integration.
- No native MCP support in this slice.
