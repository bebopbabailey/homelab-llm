# Architecture: Open Terminal

Open Terminal runs on the Mini in two separate roles:

- Native Open Terminal API on `127.0.0.1:8010` remains an optional Open WebUI
  interactive terminal path.
- Open Terminal MCP on `127.0.0.1:8011/mcp` is the current localhost-only
  durable tool plane backend and is registered directly in Open WebUI as a
  separate read-only MCP tool server.

The MCP slice is intentionally narrow:
- Dockerized runtime derived from the pinned upstream image
- read-only bind mount of `/home/christopherbailey/homelab-llm`
- named home volume only
- terminal/notebook features disabled
- current Open WebUI allowlist is `health_check`, `list_files`, `read_file`,
  `grep_search`, `glob_search`
- any future shared LiteLLM MCP lane should allowlist only repo-inspection tools

This service does not change OpenHands. OpenHands remains denied for `/v1/mcp/*`.
