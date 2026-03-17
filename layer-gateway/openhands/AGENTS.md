# Agent Guidance: OpenHands

## Scope
- Mini-local OpenHands Phase A bring-up only.
- Docker sandbox only.
- Localhost-only UI contract on `127.0.0.1:4031`.

## Guardrails
- Do not add LAN or tailnet exposure.
- Do not mount `/home/christopherbailey/homelab-llm` into the sandbox.
- Do not store provider or LiteLLM secrets in repo files or shared host env.
- Do not wire LiteLLM in this phase.
- Do not add GitHub integration, deploy rights, or auto-merge behavior.

## Runtime contract
- Primary launch path is Docker-direct.
- `openhands serve` is secondary/operator-only because the documented CLI path
  centers on `localhost:3000` and does not provide a clear Phase A port-control
  contract.

## Verification
- Confirm `127.0.0.1:4031` is reachable.
- Confirm only the disposable workspace is mounted into `/workspace`.
- Confirm a scratch-repo task completes `plan -> patch -> validate -> summarize`.
