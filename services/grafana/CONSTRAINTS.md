# Constraints: grafana

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Interface layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep Grafana bound to `127.0.0.1:3001`; remote operator access must proxy through tailnet-only `svc:grafana`.
- Keep secrets (admin credentials, API keys, datasource tokens) out of git.
- Prefer repo-managed dashboards/provisioning artifacts; avoid undocumented UI-only drift.
- Preserve observability role; no cross-service control actions from Grafana changes.

## Allowed operations
- Update dashboards/provisioning/docs in this service.
- Restart/check `grafana-server.service`.
- Perform read-only health and log diagnostics.

## Forbidden operations
- New LAN exposure or bind/port changes without explicit approval.
- Relaxing auth/security settings without an approved plan.
- Cross-layer runtime changes outside interface scope.

## Sandbox permissions
- Read: `layer-interface/*`
- Write: this service docs/config only
- Execute: Grafana restart/health/log commands only

## Validation pointers
- `curl -fsS http://127.0.0.1:3001/api/health | jq .`
- `tailscale serve status --json | jq .`
- `journalctl -u grafana-server.service -n 200 --no-pager`
- `systemctl status grafana-server.service --no-pager`

## Change guardrail
If bind/port, auth posture, or exposure policy changes, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs per `docs/_core/CHANGE_RULES.md`.
