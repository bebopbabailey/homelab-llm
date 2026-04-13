# Constraints: open-webui

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Interface layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep Open WebUI as UI/orchestration only; do not make it call inference backends directly.
- Preserve LiteLLM as the single LLM gateway path.
- Current deployment bind is `0.0.0.0:3000`; any bind/port changes require an approved migration plan and canon doc updates.
- Keep secrets in `/etc/open-webui/env`; never commit credentials or tokens.

## Allowed operations
- UI config/doc updates inside this service.
- Restart and health/log checks for `open-webui.service`.
- Safe diagnostics for web search and LiteLLM integration behavior.

## Forbidden operations
- New LAN exposure or host-binding changes without explicit approval.
- Bypassing LiteLLM by wiring direct backend endpoints into default client flows.
- Cross-layer changes outside interface scope unless explicitly requested.

## Sandbox permissions
- Read: `services/open-webui/*` plus `layer-interface/*` guidance
- Write: this service docs/config only
- Execute: Open WebUI restart/health/log commands only

## Validation pointers
- `curl -fsS http://127.0.0.1:3000/health`
- `journalctl -u open-webui.service -n 200 --no-pager`
- `curl -fsS http://127.0.0.1:4000/health/readiness`

## Change guardrail
If model pathing, auth expectations, or bind/port behavior changes, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs per `docs/_core/CHANGE_RULES.md`.
