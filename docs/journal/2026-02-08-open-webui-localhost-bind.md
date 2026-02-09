# 2026-02-08 — Open WebUI Localhost Bind

## Goal
Remove LAN exposure for Open WebUI and require access via Tailscale Serve.

## Changes
- Open WebUI systemd unit now binds to `127.0.0.1:3000`.
- Topology/docs updated to reflect local-only binding and tailnet access.

## Notes
- Tailscale Serve provides HTTPS entrypoint; LAN IP:port should no longer work.
