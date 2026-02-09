# 2026-02-08 — OptiLLM Local Deferred + Tailnet Services

## Summary
- OptiLLM local inference on the Studio is **deferred** due to latency.
- Studio runtime for opti-local is **removed**; only optillm-proxy remains.
- opti-local artifacts are **archived** in `docs/archive/optillm-local/`.
- Tailnet HTTPS services on the Mini now use **Tailscale Services** hostnames:
  `code/chat/gateway/search.<tailnet>`.
- ACLs were migrated to **grants** for service access.
- Tailscale SSH enabled on the Mini for browser-based SSH console.

## Notes
- OptiLLM local inference is reserved for the future Orin AGX (CUDA) node.
- Service access should be granted with `svc:*` grants (not legacy ACLs).
