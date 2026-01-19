# Interface Layer Constraints

## Hard constraints
- Do not call model backends directly. All traffic goes through LiteLLM.
- Do not expose new LAN services without approval.
- Do not store secrets in the repo.

## Sandbox permissions
- Read: `layer-interface/*`
- Write: `layer-interface/*` docs and configs only
- Execute: restart interface services only (e.g., Open WebUI)
- Forbidden: changes to gateway/inference/tools/data layers

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.
