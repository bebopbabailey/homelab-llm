# Inference Layer Constraints

## Hard constraints
- No direct client access; only the gateway calls this layer.
- Do not install system drivers or use global pip without approval.
- Do not modify or restart `ollama`.

## Sandbox permissions
- Read: `layer-inference/*`
- Write: inference docs/configs by default; service-local docs/code/configs only
  when the service bundle explicitly allows them
- Execute: service-local diagnostics and restarts only when the service runbook
  explicitly allows them
- Forbidden: system driver installs, global pip, touching ollama
