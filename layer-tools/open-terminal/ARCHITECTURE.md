# Architecture: Open Terminal

Open Terminal runs on the Mini in two separate roles:

- Native Open Terminal API on `127.0.0.1:8010` remains an optional Open WebUI
  convenience path for human terminal UX.
- Open Terminal MCP on `127.0.0.1:8011/mcp` is the current localhost-only
  durable tool plane backend.

The MCP slice is intentionally narrow:
- Dockerized runtime derived from the pinned upstream image
- read-only bind mount of `/home/christopherbailey/homelab-llm`
- named home volume only
- terminal/notebook features disabled
- any future shared LiteLLM MCP lane should allowlist only repo-inspection tools

This service does not change OpenHands. OpenHands remains denied for `/v1/mcp/*`.
