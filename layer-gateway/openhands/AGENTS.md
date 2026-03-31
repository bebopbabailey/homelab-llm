# Agent Guidance: OpenHands

## Scope
- Mini-local OpenHands Phase A managed runtime and operator workflow.
- Docker sandbox only.
- Localhost-only UI contract on `127.0.0.1:4031`.

## Guardrails
- Do not add LAN or public exposure.
- Do not change tailnet exposure outside the dedicated `svc:hands` mapping.
- Do not mount `/home/christopherbailey/homelab-llm` into the sandbox.
- Do not store provider or LiteLLM secrets in repo files or `/etc/openhands/env`.
- Do not wire LiteLLM in this phase.
- Do not add GitHub integration, deploy rights, or auto-merge behavior.

## Runtime contract
- Primary launch path is the repo-managed `systemd` unit
  `platform/ops/systemd/openhands.service`, installed as
  `/etc/systemd/system/openhands.service`.
- Runtime vars live in `/etc/openhands/env` and must remain non-secret.
- `openhands serve` is secondary/operator-only because the documented CLI path
  centers on `localhost:3000` and does not provide a clear Phase A port-control
  contract.

## Verification
- Confirm `openhands.service` is enabled and active.
- Confirm `127.0.0.1:4031` is reachable.
- Confirm `https://hands.tailfd1400.ts.net/` is reachable from another tailnet node.
- Confirm only the disposable workspace is mounted into `/workspace`.
- Confirm a scratch-repo task completes `plan -> patch -> validate -> summarize`.
