# Interface Layer Constraints

## Hard constraints
- Do not call external LLM/model backends directly. LLM traffic goes through
  LiteLLM.
- Local service-bound STT/TTS engines are allowed when the service contract
  explicitly permits them.
- Do not expose new LAN services without approval.
- Do not store secrets in the repo.

## Sandbox permissions
- Read: `layer-interface/*`
- Write: `layer-interface/*` docs and configs only
- Execute: restart interface services only (e.g., Open WebUI)
- Forbidden: changes to gateway/inference/tools/data layers

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.
