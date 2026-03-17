# OpenHands (Mini Phase A)

OpenHands here is a local, operator-supervised coding worker for the Mini.
Phase A is intentionally narrow:

- Docker sandbox only
- local UI on `127.0.0.1:4031`
- optional tailnet-only operator access on `https://hands.tailfd1400.ts.net/`
- disposable workspace only
- temporary provider/API key entered in the UI only
- no LiteLLM dependency yet

This service boundary exists to prove worker mechanics safely before any
gateway-policy handoff.

## Status
- Phase A: active bring-up path
- Docker-direct smoke validated on the Mini: UI responds on `127.0.0.1:4031`
- Not an always-on service
- Tailnet exposure is allowed only through dedicated Tailscale Service `svc:hands`
- Not LAN or public internet exposed
- Not allowed to mount the live monorepo in this phase
- First provider-backed scratch-repo task loop still pending manual operator run

OpenCode boundary:
- OpenCode Web now uses dedicated Tailscale Service `svc:codeagent`
- OpenHands work on `svc:hands` must not modify the separate OpenCode mapping

## Primary launch path
1. Install CLI/tools:
   `uv tool install openhands --python 3.12`
2. Launch the app with the Docker-direct contract documented in `RUNBOOK.md`.

`openhands serve` remains secondary/operator-only. The installed CLI still
centers that launcher on `localhost:3000`, which conflicts with the Mini's
existing Open WebUI bind.

## Future handoff
Phase B swaps the temporary direct provider for LiteLLM only after the
LiteLLM alias/key/policy contract is finalized.
