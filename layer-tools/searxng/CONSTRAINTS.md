# Constraints: searxng

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Tools layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep SearXNG local-only on `127.0.0.1:8888` unless explicitly approved.
- Do not introduce Docker-based deployment changes from this service boundary.
- Keep secrets and engine credentials out of git.
- Preserve tool/search role only; no direct LLM gateway replacement behavior.

## Allowed operations
- Update service docs and safe config for approved search behavior.
- Restart/check `searxng.service`.
- Run read-only health/log checks.

## Forbidden operations
- New LAN exposure or bind/port changes without explicit approval.
- Enabling new external integrations that alter security posture without design approval.
- Cross-layer runtime edits outside tools scope.

## Sandbox permissions
- Read: `layer-tools/*`
- Write: this service docs/config only
- Execute: SearXNG restart/health/log commands only

## Validation pointers
- `curl -fsS http://127.0.0.1:8888`
- `journalctl -u searxng.service -n 200 --no-pager`
- `systemctl status searxng.service --no-pager`

## Change guardrail
If bind/port, exposure posture, or integration behavior changes, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs per `docs/_core/CHANGE_RULES.md`.
