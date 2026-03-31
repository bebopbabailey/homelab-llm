# Service Spec: OpenHands (Mini Phase A)

## Purpose
Provide a safe, local first-run environment for OpenHands on the Mini so the
homelab can validate coding-worker mechanics before LiteLLM integration.

## Status
- Managed always-on Phase A UI baseline
- Primary launch path: repo-managed `systemd` + Docker runtime
- Installed host unit: `/etc/systemd/system/openhands.service`
- Installed host env file: `/etc/openhands/env`

## Inbound / outbound
- Inbound: `http://127.0.0.1:4031`
- Tailnet-only inbound: `https://hands.tailfd1400.ts.net/` via `svc:hands`
- Outbound in Phase A: temporary operator-selected model provider from the UI
- Outbound in Phase B: LiteLLM only, using the governed worker contract:
  - `Custom Model = litellm_proxy/code-reasoning`
  - `API Key = openhands-worker`
  - canonical container path: `http://host.docker.internal:4000/v1`
  - verified fallback/reference path: `http://192.168.1.71:4000/v1`

## Runtime owner
- `openhands.service` launches Docker container `openhands-app`
- Repo-managed unit source: `platform/ops/systemd/openhands.service`
- Non-secret runtime vars source: `platform/ops/templates/openhands.env.example`

## Workspace / state
- Disposable workspace mount target in sandbox: `/workspace`
- Preferred host workspace path: `/home/christopherbailey/openhands-experimental/phase-a-workspace`
- Preferred host persistence path: `/home/christopherbailey/.local/share/openhands-phasea`
- If custom host persistence mount is not honored, fallback to the documented
  `~/.openhands:/.openhands` bind for the session and clean it up afterward

## Security rules
- Docker sandbox only
- Localhost bind at `127.0.0.1:4031`
- Tailnet-only remote access must use `svc:hands`
- `/etc/openhands/env` may contain only non-secret runtime vars
- No live monorepo mount
- No GitHub integration, deploy rights, or auto-merge

## Verification contract
- `systemctl is-enabled openhands.service` returns `enabled`
- `systemctl is-active openhands.service` returns `active`
- UI responds on `127.0.0.1:4031`
- Tailscale Serve exposes the same UI at `https://hands.tailfd1400.ts.net/`
- `docker inspect openhands-app --format '{{json .HostConfig.Binds}}'` shows
  only Docker socket + persistence binds
- `SANDBOX_VOLUMES=...:/workspace:rw` is present in the app container env for
  future sandbox launches
- remote tailnet root returns `200`
- scratch-repo validation command passes inside the sandbox flow
- Phase B LiteLLM handoff uses one reserved/internal worker alias only:
  `code-reasoning -> deep`
- Worker contract is Chat Completions-first
- MCP remains denied
- `/v1/responses` remains denied
