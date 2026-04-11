# Constraints: ov-llm-server

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Inference layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep service port at `9000` unless an approved migration updates canon docs.
- Do not touch or modify `ollama` (port `11434`).
- Use `uv` for dependency management; no global `pip` installs.
- Do not install system drivers from this service workflow.
- Preserve OpenAI-compatible endpoint contract (`/v1/chat/completions`, `/v1/models`, `/health`).

## Allowed operations
- Update service docs/config templates and OpenVINO server implementation in-scope.
- Restart/check `ov-server.service` and run local health checks.
- Maintain registry-backed model loading and lazy-load behavior unless explicitly changed.

## Forbidden operations
- New LAN exposure, bind/port changes, or host-binding changes without explicit approval.
- Secret material in repo (tokens/credentials/env values).
- Cross-service runtime changes outside this inference boundary.

## Sandbox permissions
- Read: `layer-inference/*`
- Write: this service docs/config/code in-scope only
- Execute: OpenVINO service health/log checks and restart commands only

## Validation pointers
- `curl -fsS http://127.0.0.1:9000/health | jq .`
- `curl -fsS http://127.0.0.1:9000/v1/models | jq .`
- `journalctl -u ov-server.service -n 200 --no-pager`

## Change guardrail
If endpoint contract, bind/port, or exposure policy changes, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs per `docs/_core/CHANGE_RULES.md`.
