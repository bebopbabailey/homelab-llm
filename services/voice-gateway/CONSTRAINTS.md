# Constraints: voice-gateway

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Interface layer: `../CONSTRAINTS.md`

## Hard constraints
- LiteLLM is the required path for future LLM calls from this service.
- Local STT/TTS engines inside the Voice Gateway service boundary are allowed.
- Do not call MLX, OpenVINO, OptiLLM, or other external inference backends
  directly from this service.
- Do not change public/LAN exposure or host binding without explicit approval.
- Keep secrets out of git.

## Allowed operations
- Voice-gateway-local docs/config/code changes within this service boundary.
- Validation of gateway integrations and service-local health checks.
- Read-only diagnostics for downstream dependencies.

## Forbidden operations
- Backend bypass around LiteLLM.
- New public/LAN exposure, port changes, or bind changes without approval.
- Cross-layer runtime modifications outside interface scope.

## Sandbox permissions
- Read: `services/voice-gateway/*` plus `layer-interface/*` guidance
- Write: this service docs/config/code only
- Execute: service-local diagnostics only

## Validation pointers
- `test -f services/voice-gateway/SERVICE_SPEC.md`
- `test -f services/voice-gateway/RUNBOOK.md`

## Change guardrail
If voice routing, exposure, or backend pathing changes, update `SERVICE_SPEC.md`, `RUNBOOK.md`, and platform docs in the same change.
