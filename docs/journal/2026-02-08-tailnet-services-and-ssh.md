# 2026-02-08 — Tailnet Services + SSH Console

## Summary
- Tailnet HTTPS access now uses **Tailscale Services** hostnames:
  `code/chat/gateway/search.<tailnet>`.
- Service access requires **grants** (not legacy ACLs) with `svc:*` targets.
- iPhone access validated after grants + Services host mapping.
- **Tailscale SSH** enabled on the Mini for browser-based SSH console use.

## Notes
- Direct tailnet IP:port access remains unless explicitly denied by policy.
- Services are configured on the Mini with `tailscale serve --service=svc:<name>`.
- SSH console availability depends on:
  - `tailscale set --ssh=true` on the host
  - SSH policy allowing the user to `tag:homelab`
