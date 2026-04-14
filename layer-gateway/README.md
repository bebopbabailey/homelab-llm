# Gateway Layer

Mission: client-facing model/API routing plus adjacent gateway-side operator
surfaces.

For client-facing model/API traffic, LiteLLM remains the only approved gateway.
Other services in this layer are operator or orchestration surfaces, not
alternate client paths to inference backends.

This layer no longer contains live service roots. It remains as a transitional
taxonomy and layer-doc surface while the final `vector-db` move and the
remaining layer-level registry/docs cleanup land elsewhere.

Recently moved service roots:
- `services/litellm-orch`
- `services/optillm-proxy`
- `services/openhands`
- `services/tiny-agents`
- `experiments/system-monitor`

## Gateway handles registry
- Source of truth: `layer-gateway/registry/handles.jsonl`
- Use `scripts/validate_handles.py` to validate schema + uniqueness

## System monitor model
- Monitor is read-only
- Monitor does not restart services
- Overseer or layer/service agents perform restarts and repairs
