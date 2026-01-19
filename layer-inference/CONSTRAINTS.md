# Inference Layer Constraints

## Hard constraints
- No direct client access; only the gateway calls this layer.
- Do not install system drivers or use global pip without approval.
- Do not modify or restart `ollama`.

## Sandbox permissions
- Read: `layer-inference/*`
- Write: inference configs + docs only
- Execute: restart inference services only (OpenVINO, MLX/Studio via ops)
- Forbidden: system driver installs, global pip, touching ollama

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.
