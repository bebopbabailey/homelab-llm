# OpenHands (Mini Phase A)

OpenHands here is a managed local coding-worker surface on the Mini. Phase A
remains intentionally narrow:

- Docker sandbox only
- local UI on `127.0.0.1:4031`, supervised by `systemd`
- tailnet-only operator access on `https://hands.tailfd1400.ts.net/` via `svc:hands`
- disposable workspace only
- temporary provider/API key entered in the UI only
- no LiteLLM dependency yet

This service boundary exists to keep the UI reliably available while still
proving worker mechanics safely before any gateway-policy handoff.

## Status
- Phase A: managed local UI baseline
- Repo-managed runtime: `platform/ops/systemd/openhands.service`
- Host runtime files: `/etc/systemd/system/openhands.service`, `/etc/openhands/env`
- Tailnet exposure is allowed only through dedicated Tailscale Service `svc:hands`
- Not LAN or public internet exposed
- Not allowed to mount the live monorepo in this phase
- First provider-backed scratch-repo task loop still pending manual operator run
- The runtime sandbox image is not cached yet; first sandbox execution remains a
  separate explicit step

OpenCode boundary:
- OpenCode Web uses dedicated Tailscale Service `svc:codeagent`
- OpenHands work on `svc:hands` must not modify the separate OpenCode mapping

## Primary launch path
Install the repo-managed systemd unit and non-secret env file documented in
`RUNBOOK.md`, then let `openhands.service` own the Docker runtime.

`openhands serve` remains secondary/operator-only. The installed CLI still
centers that launcher on `localhost:3000`, which conflicts with the Mini's
existing Open WebUI bind and does not provide the managed runtime contract this
service now expects.

## Future handoff
Phase B swaps the temporary direct provider for LiteLLM only after the
LiteLLM alias/key/policy contract is finalized.
