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
- Write: interface docs/configs by default; service-local docs/code/configs only
  when the service bundle explicitly allows them
- Execute: service-local diagnostics and restarts only when the service runbook
  explicitly allows them
- Forbidden: changes to gateway/inference/tools/data layers

Respect global constraints: `/home/christopherbailey/homelab-llm/CONSTRAINTS.md`.
