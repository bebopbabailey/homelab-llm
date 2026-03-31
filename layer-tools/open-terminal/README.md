# Open Terminal

## Purpose
Provide a boring, durable terminal-inspection surface on the Mini without
changing the current LiteLLM-centered model contract.

## Runtime shape
- Native API container for Open WebUI human UX: `127.0.0.1:8010`
- MCP container for localhost-only tooling: `127.0.0.1:8011/mcp`
- Both stay localhost-only

## First-slice scope
- Bind mount: `/home/christopherbailey/homelab-llm:/lab/homelab-llm:ro`
- Current live MCP path is the localhost-only direct backend on `127.0.0.1:8011/mcp`.
- A shared LiteLLM MCP alias for the read-only subset remains follow-on work.
- Explicitly not exposed in slice 1:
  - `display_file`
  - `write_file`
  - `replace_file_content`
  - `list_processes`
  - `run_command`
  - `get_process_status`
  - `send_process_input`
  - `kill_process`

## Security posture
- No `docker.sock`
- No whole-host bind mounts
- No write mount for the repo
- No LAN exposure
- Direct backend remains localhost-only; any future shared LiteLLM MCP path
  would become the durable auth/policy boundary

## Build
```bash
docker build -t local/open-terminal-mcp:0.11.29 \
  -f /home/christopherbailey/homelab-llm/layer-tools/open-terminal/Dockerfile.mcp \
  /home/christopherbailey/homelab-llm
```

## Validate
See `RUNBOOK.md`.
