# 12-DECISIONS_LOG

## 2026-01-03 - LiteLLM as the single gateway (accepted)
- Decision: Use LiteLLM proxy as the only OpenAI-compatible entry point.
- Status: accepted
- Rationale: Centralize routing, health checks, and logging in one gateway.
- Evidence: `01-PLATFORM_TOPOLOGY.md`, `04-INTEGRATIONS_LITELLM.md`

## 2026-01-03 - Plain logical model names (accepted)
- Decision: Client-facing model names are plain (`jerry-*`, `lil-jerry`) while upstream routing uses `openai/<upstream>`.
- Status: accepted
- Rationale: Keep `/v1/models` clean and provider-agnostic.
- Evidence: `04-INTEGRATIONS_LITELLM.md`

## 2026-01-03 - Open WebUI points to LiteLLM (accepted)
- Decision: Open WebUI uses LiteLLM via `OPENAI_API_BASE_URL` on 127.0.0.1:4000/v1.
- Status: accepted
- Rationale: UI remains a thin client; gateway handles routing.
- Evidence: `05-INTEGRATIONS_OPENWEBUI.md`, `02-PORTS_ENDPOINTS_REGISTRY.md`

## 2026-01-03 - OpenVINO stays behind LiteLLM (accepted)
- Decision: OpenVINO backend is accessed via LiteLLM routing (`lil-jerry`).
- Status: accepted
- Rationale: Maintain a single gateway and consistent auth/logging patterns.
- Evidence: `06-INTEGRATIONS_OPENVINO.md`, `04-INTEGRATIONS_LITELLM.md`

## 2026-01-03 - Ports treated as immutable (accepted)
- Decision: Current ports are fixed unless an explicit migration phase is added.
- Status: accepted
- Rationale: Avoid client breakage and hidden conflicts on the LAN.
- Evidence: `02-PORTS_ENDPOINTS_REGISTRY.md`
