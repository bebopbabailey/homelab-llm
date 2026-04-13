# Gateway Layer

Mission: client-facing model/API routing plus adjacent gateway-side operator
surfaces.

For client-facing model/API traffic, LiteLLM remains the only approved gateway.
Other services in this layer are operator or orchestration surfaces, not
alternate client paths to inference backends.

Live service roots still in this layer:
- `layer-gateway/litellm-orch`
- `layer-gateway/openhands`
- `layer-gateway/optillm-proxy`

Recently moved service roots:
- `services/tiny-agents`
- `experiments/system-monitor`

## Gateway handles registry
- Source of truth: `layer-gateway/registry/handles.jsonl`
- Use `scripts/validate_handles.py` to validate schema + uniqueness

## System monitor model
- Monitor is read-only
- Monitor does not restart services
- Overseer or layer/service agents perform restarts and repairs
