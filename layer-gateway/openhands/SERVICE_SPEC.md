# Service Spec: OpenHands (Mini Phase A)

## Purpose
Provide a safe, local first-run environment for OpenHands on the Mini so the
homelab can validate coding-worker mechanics before LiteLLM integration.

## Status
- Operator-launched only
- Docker-direct primary launch path
- Not enabled as a systemd service in Phase A

## Inbound / outbound
- Inbound: `http://127.0.0.1:4031`
- Optional tailnet-only inbound: `https://hands.tailfd1400.ts.net/` via `svc:hands`
- Outbound in Phase A: temporary operator-selected model provider from the UI
- Outbound in Phase B: LiteLLM only, via the current app-container-reachable
  gateway path `http://192.168.1.71:4000/v1`
- The current bridge-mode app container does not reach LiteLLM at
  `http://host.docker.internal:4000/v1`

## Workspace / state
- Disposable workspace mount target in sandbox: `/workspace`
- Preferred host workspace path: `/home/christopherbailey/openhands-experimental/phase-a-workspace`
- Preferred host persistence path: `/home/christopherbailey/.local/share/openhands-phasea`
- If custom host persistence mount is not honored, fallback to the documented
  `~/.openhands:/.openhands` bind for the session and clean it up afterward

## Security rules
- Docker sandbox only
- Localhost bind at `127.0.0.1:4031`
- Tailnet-only remote access, if enabled, must use `svc:hands`
- No shared host env file in Phase A
- No live monorepo mount
- No GitHub integration, deploy rights, or auto-merge

## Verification contract
- UI responds on `127.0.0.1:4031`
- Tailscale Serve may expose the same UI at `https://hands.tailfd1400.ts.net/`
- `docker inspect` shows only the expected binds
- scratch-repo validation command passes inside the sandbox flow
- Phase B LiteLLM gate is ready only when the app-container-reachable LiteLLM
  URL succeeds on `code-reasoning`, denies `main`, denies `/v1/mcp/tools`, and
  worker traffic is attributable to `key_alias=openhands-worker`
