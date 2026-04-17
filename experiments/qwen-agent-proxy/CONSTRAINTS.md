# Constraints: qwen-agent-proxy

This service inherits global constraints:
- Global: `../../CONSTRAINTS.md`

## Hard constraints
- Remain localhost-only on the Mini.
- Stay experimental and shadow-only.
- Do not replace the trusted `code-reasoning` worker lane.
- Keep auth material and local service tokens out of git.
- Do not expose `/v1/responses` in this slice.

## Allowed operations
- Service-local code, docs, and startup wrapper updates.
- Localhost-only systemd wiring.
- Validation through direct sidecar calls, shadow LiteLLM, and OpenHands shadow checks.

## Forbidden operations
- New LAN or tailnet exposure.
- Public alias promotion.
- Direct Open WebUI or OpenCode wiring in this slice.

## Validation pointers
- `curl -fsS http://127.0.0.1:4021/health`
- `curl -fsS -H "Authorization: Bearer $QWEN_AGENT_PROXY_AUTH_TOKEN" http://127.0.0.1:4021/v1/models | jq .`
- `curl -fsS -H "Authorization: Bearer $QWEN_AGENT_PROXY_AUTH_TOKEN" http://127.0.0.1:4021/v1/chat/completions ...`
