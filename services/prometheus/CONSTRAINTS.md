# Constraints: prometheus

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Tools layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep Prometheus local-only on `127.0.0.1:9090` unless explicitly approved.
- Treat scrape config as infrastructure-critical; changes must stay minimal and documented.
- Do not commit secrets or credentials in repo-managed config.
- Preserve monitoring role only; no service control side effects from Prometheus config.

## Allowed operations
- Update scrape/provisioning docs and safe config entries.
- Restart and check `prometheus.service`.
- Add read-only health/target diagnostics.

## Forbidden operations
- New LAN exposure or bind/port changes without explicit approval.
- Ad-hoc retention/storage policy changes without an explicit plan.
- Cross-layer runtime modifications from this service boundary.

## Sandbox permissions
- Read: `layer-tools/*`
- Write: this service docs/config only
- Execute: Prometheus restart/health/log commands only

## Validation pointers
- `curl -fsS http://127.0.0.1:9090/-/ready`
- `curl -fsS http://127.0.0.1:9090/-/healthy`
- `journalctl -u prometheus.service -n 200 --no-pager`

## Change guardrail
If scrape topology, bind/port, or exposure policy changes, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs per `docs/_core/CHANGE_RULES.md`.
