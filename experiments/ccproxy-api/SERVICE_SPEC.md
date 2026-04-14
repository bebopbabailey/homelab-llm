# Service Spec: ccproxy-api

## Purpose
Experimental localhost-only CCProxy sidecar for Codex-backed chat on the Mini.
This service exists so LiteLLM can route `chatgpt-5` through a cleaner OpenAI-
compatible backend than the raw `chatgpt.com/backend-api/codex` path.

## Host & Runtime
- Host: Mini
- Runtime: Python CLI (`ccproxy-api`)
- Bind: `127.0.0.1:4010`
- Exposure: localhost only
- Systemd unit: `ccproxy-api.service`

## Endpoints
- `GET /codex/v1/models`
- `POST /codex/v1/chat/completions`
- `POST /codex/v1/responses`

## Auth
- Local bearer token via `/etc/homelab-llm/ccproxy.env`
- OAuth/Codex auth comes from local user state such as `~/.codex/auth.json`
- No auth state or service token is tracked in git

## Current contract
- Intended downstream consumer: LiteLLM only
- Validated model ids on the current account are Codex-family ids reported by
  `/codex/v1/models`
- Current experimental LiteLLM alias `chatgpt-5` maps to `gpt-5.3-codex`
- Chat Completions is the primary path for Open WebUI usability
- Responses remains available for operator/debug use

## Notes
- This service is experimental and not a stable public contract.
- The lane is subscription-backed and account-sensitive.
