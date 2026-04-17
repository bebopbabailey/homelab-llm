# AGENTS — qwen-agent-proxy

## Scope
- Maintain the experimental `qwen-agent-proxy` sidecar only.
- Keep it localhost-only and scoped to the OpenHands shadow lane.

## Read First
- `SERVICE_SPEC.md`
- `ARCHITECTURE.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Runtime Reality
- Host: Mini.
- Bind: `127.0.0.1:4021` only.
- This service is an adapter sidecar for Qwen-Agent over the Studio
  `Qwen3-Coder-Next` shadow backend.

## Change Guardrails
- No LAN exposure, port changes, or auth removal without explicit approval.
- Keep backend and service tokens out of git.
- Keep the LiteLLM/OpenHands shadow docs in sync with the service contract.
