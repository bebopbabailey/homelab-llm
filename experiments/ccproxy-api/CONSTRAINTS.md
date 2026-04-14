# Constraints: ccproxy-api

This service inherits global constraints:
- Global: `../../CONSTRAINTS.md`

## Hard constraints
- Remain localhost-only on the Mini.
- Stay behind LiteLLM for user-facing flows.
- Keep all auth state and bearer tokens out of git.
- Do not treat this lane as a stable public contract.

## Allowed operations
- Service-local docs, config, and startup wrapper updates.
- Systemd wiring for localhost-only operation.
- Validation of the Codex-backed OpenAI-compatible path.

## Forbidden operations
- New LAN or tailnet exposure.
- Direct Open WebUI -> CCProxy wiring as the default path.
- Secret commits or repo-tracked auth files.

## Validation pointers
- `curl -fsS -H "Authorization: Bearer $CCPROXY_AUTH_TOKEN" http://127.0.0.1:4010/codex/v1/models | jq .`
- `curl -fsS -H "Authorization: Bearer $CCPROXY_AUTH_TOKEN" http://127.0.0.1:4010/codex/v1/chat/completions ...`

## Change guardrail
If the bind, auth model, or LiteLLM routing changes, update platform docs and
the LiteLLM service docs in the same change.
