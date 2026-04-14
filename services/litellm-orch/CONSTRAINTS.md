# Constraints: litellm-orch

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Gateway layer: `../CONSTRAINTS.md`

## Hard constraints
- Remain a gateway/routing service only. No inference runtime changes in this service.
- Current deployment bind is `0.0.0.0:4000`; localhost use remains valid, and
  Studio upstreaming uses the Mini LAN URL `http://192.168.1.71:4000/v1`.
- Preserve auth requirements for API and health surfaces as documented in canonical docs.
- Keep client contract as LiteLLM-first; do not introduce direct client -> backend paths.
- For Studio team lanes (`8100-8119`), keep `mlxctl` as source of truth (`sync-gateway` flow).

## Allowed operations
- Update `config/router.yaml` and service docs to reflect approved routing changes.
- Restart/check LiteLLM service on Mini for validation.
- Add or adjust read-only diagnostics and health checks.

## Forbidden operations
- New LAN exposure, bind/port changes, or host-binding changes without explicit approval.
- Committing secrets (`config/env.local`, keys, tokens).
- Directly managing MLX runtime by bypassing `mlxctl` policy for team lanes.

## Sandbox permissions
- Read: `layer-gateway/*`
- Write: gateway configs + docs only
- Execute: gateway service checks/restarts only

## Validation pointers
- `curl -fsS http://127.0.0.1:4000/health/readiness`
- `curl -fsS http://192.168.1.71:4000/health/readiness`
- `curl -fsS -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://192.168.1.71:4000/v1/models | jq .`
- `rg -n "modify_params|target_models|coerce_stream_false" config/router.yaml`

## Change guardrail
If runtime behavior changes (routing/auth/bind/ports), update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs per `docs/_core/CHANGE_RULES.md`.
