# AGENTS — optillm-proxy

## Scope
- Studio-hosted OptiLLM proxy used behind LiteLLM `boost*` aliases.
- This service is an upstream optimization proxy, not a primary client entrypoint.
- Source of truth: `SERVICE_SPEC.md`, `RUNBOOK.md`, `CONSTRAINTS.md`.

## Runtime Reality
- Runtime owner: launchd label `com.bebop.optillm-proxy` on Studio.
- Bind/port: `192.168.1.72:4020` for the LAN-first `boost*` path.
- Auth: no backend bearer token; rely on the dedicated Studio LAN bind and the
  LiteLLM-only caller contract.
- Upstream: Mini LiteLLM at `http://192.168.1.71:4000/v1`.
- Deployment source of truth remains this repo; deployment helper is
  `scripts/deploy_studio.sh`.

## Guardrails
- Do not add extra OptiLLM daemons/ports without explicit design approval.
- Do not relax auth or exposure constraints without approved security plan.
- Avoid routing loops (proxy -> LiteLLM -> proxy).
- No secrets in git-managed files.
- Do not reintroduce deploy-time patching.
- Do not pin OptiLLM from a git URL in this service.
- Use exact-SHA deploys only (`scripts/deploy_studio.sh`).

## Working Files
- `README.md` (operational behavior)
- `SERVICE_SPEC.md` (interface + placement contract)
- `RUNBOOK.md` (launchd operations + smoke checks)
- `CONSTRAINTS.md` (non-negotiables)
- `scripts/` (deploy and canary helpers)

## Verification Commands
```bash
curl -fsS http://192.168.1.72:4020/v1/models | jq .
curl -fsS http://192.168.1.71:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost","messages":[{"role":"user","content":"ping"}],"optillm_approach":"bon","max_tokens":16}' | jq .
```

## Change Policy
- Keep docs and runtime guidance synchronized with launchd/system topology.
- If runtime args, bind/port, auth, or upstream wiring changes, update service
  docs and canonical platform docs per `docs/_core/CHANGE_RULES.md`.
- Request-body base-model overrides are not part of the active service contract.

## Planner Policy
- Prefer `boost-plan-trio` for deliberate planning and coding workflows where
  completeness matters more than raw latency.
- Use `boost-plan` as the upstream baseline and fallback comparator.
- Do not treat `boost-plan-trio` as the universal low-latency default.
- Do not reintroduce patch-era assumptions into docs, deploy flows, or service
  contracts.
