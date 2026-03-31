# Constraints: OpenHands (Mini Phase A)

This service inherits global and gateway-layer constraints:

- Global: `../../CONSTRAINTS.md`
- Gateway layer: `../CONSTRAINTS.md`

## Hard constraints
- Keep the Phase A UI bound to `127.0.0.1:4031` only.
- Use the repo-managed `systemd` + Docker launch path as the primary runtime in
  Phase A.
- Mount only a disposable workspace into `/workspace`.
- Do not mount `/home/christopherbailey/homelab-llm` in Phase A.
- Do not store provider or LiteLLM secrets in repo files or `/etc/openhands/env`.
- Do not wire LiteLLM, GitHub integration, deploy rights, or auto-merge in this phase.
- If remote operator access is enabled, expose it only through Tailscale Service `svc:hands`.
- When validating the future LiteLLM Phase B handoff, use LiteLLM only through a
  runtime-validated app-container-reachable gateway URL. The current validated
  path is `http://192.168.1.71:4000/v1`.

## Allowed operations
- Service-local docs and runbook updates.
- Repo-managed systemd unit and non-secret env-template updates.
- systemd-managed Docker validation on `127.0.0.1:4031`.
- Tailnet-only HTTPS exposure through `https://hands.tailfd1400.ts.net/` backed by `svc:hands`.
- Disposable workspace testing.

## Forbidden operations
- New LAN exposure.
- Public internet exposure.
- Any Tailscale Serve change outside `svc:hands` in this task.
- Shared host env-file wiring for secrets.
- Direct backend calls to MLX or OpenVINO in Phase A.
- Unattended task execution or autonomous deployment workflows in Phase A.
