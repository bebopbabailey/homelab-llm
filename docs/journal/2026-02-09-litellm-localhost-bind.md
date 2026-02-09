# 2026-02-09 — LiteLLM Localhost Bind

## Goal
Remove LAN exposure for LiteLLM and require access via Tailscale Serve.

## Changes
- LiteLLM systemd unit now binds to `127.0.0.1:4000`.
- Docs updated to reflect local-only gateway access + tailnet HTTPS.

## Notes
- Health endpoint now requires auth; local checks should include bearer key.
