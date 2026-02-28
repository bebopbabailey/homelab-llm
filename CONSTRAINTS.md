# Constraints: optillm-proxy

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Gateway layer: `../CONSTRAINTS.md`

## Hard constraints
- Preserve LiteLLM-first client contract; this proxy is an upstream for LiteLLM `boost*` routes.
- Keep listener and bind on Studio (`0.0.0.0:4020`) unless an approved migration updates canon docs.
- Keep authorization enforcement on proxy endpoints.
- Avoid routing loops (proxy -> LiteLLM -> proxy); upstream changes must be explicit and documented.
- Keep secrets and runtime keys out of git-managed files.

## Allowed operations
- Update proxy docs and non-secret config for approved behavior.
- Restart/inspect launchd unit (`com.bebop.optillm-proxy`) for validation.
- Add read-only diagnostics for router/plugin health.

## Forbidden operations
- Exposing additional ports/endpoints without explicit approval.
- Relaxing auth requirements without an approved security plan.
- Introducing extra proxy daemons to split handles without explicit design approval.

## Sandbox permissions
- Read: `layer-gateway/*`
- Write: proxy docs/config in this service only
- Execute: proxy health checks and launchd restart commands only

## Validation pointers
- `curl -fsS http://127.0.0.1:4020/v1/models -H "Authorization: Bearer $OPTILLM_API_KEY" | jq .`
- `rg -n "Router predicted approach|Error in router plugin|Falling back to direct model usage" /Users/thestudio/Library/Logs/optillm-proxy.log /Users/thestudio/Library/Logs/optillm-proxy.err | tail -n 80`
- `curl -fsS http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_API_KEY" -H "Content-Type: application/json" -d '{"model":"boost","messages":[{"role":"user","content":"ping"}],"optillm_approach":"bon","max_tokens":16}' | jq .`

## Change guardrail
If launchd/runtime args, upstream wiring, auth, or bind/port behavior changes, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs per `docs/_core/CHANGE_RULES.md`.
