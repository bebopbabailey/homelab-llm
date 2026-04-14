# AGENTS — ccproxy-api

## Scope
- Maintain the experimental `ccproxy-api` sidecar only.
- Keep it localhost-only and behind LiteLLM.

## Read First
- `SERVICE_SPEC.md`
- `ARCHITECTURE.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Runtime Reality
- Host: Mini.
- Bind: `127.0.0.1:4010` only.
- This service is an operator-side localhost backend for LiteLLM; Open WebUI
  must not call it directly.

## Change Guardrails
- No LAN exposure, port changes, or auth removal without explicit approval.
- Keep auth material and tokens out of git.
- Keep the LiteLLM alias contract and this service docs in sync.
