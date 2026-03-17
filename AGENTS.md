# AGENTS — litellm-orch

## Scope
- Mini-hosted LiteLLM gateway service for client routing, auth, retries,
  fallbacks, and generic tool/search proxying.
- This service is routing-only; it must not implement inference.

## Read First
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Runtime Reality
- Bind stays `0.0.0.0:4000`; on-host callers can still use `127.0.0.1:4000`.
- Canonical Studio upstream path to LiteLLM is the Mini LAN URL
  `http://192.168.1.71:4000/v1`.
- Team MLX lanes `8100-8119` remain `mlxctl`-managed.
- Client contract stays LiteLLM-first; do not introduce direct client-to-backend
  paths.
- OpenCode repo-work defaults are documented in `/home/christopherbailey/homelab-llm/docs/OPENCODE.md`,
  not in this service-local file.

## Change Guardrails
- No bind, port, auth, or routing changes without updating canonical docs per
  `docs/_core/CHANGE_RULES.md`.
- No secrets in `config/env.local` or other git-managed files.
- Keep `config/router.yaml`, service docs, and handle-validation expectations in
  sync.

## Validation
- `curl -fsS http://127.0.0.1:4000/health/readiness`
- `curl -fsS http://192.168.1.71:4000/health/readiness`
- `curl -fsS -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://192.168.1.71:4000/v1/models | jq .`
- `rg -n "modify_params|target_models|coerce_stream_false" config/router.yaml`
