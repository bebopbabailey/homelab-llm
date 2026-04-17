# Service Spec: Open Terminal MCP

## Purpose
Read-only Open Terminal MCP backend on the Mini for repo inspection. This
service is live as a localhost-only direct MCP backend and does not replace the
native Open WebUI Open Terminal integration on `127.0.0.1:8010`.

## Host & Runtime
- **Host**: Mini
- **Runtime**: Docker under systemd
- **Image**: derived from pinned upstream `ghcr.io/open-webui/open-terminal`
- **Bind**: `127.0.0.1:8011->8000`
- **MCP endpoint**: `http://127.0.0.1:8011/mcp`

## Command
```bash
mcp --transport streamable-http --host 0.0.0.0 --port 8000 --cwd /lab/homelab-llm
```

## Container posture
- repo root mounted read-only at `/lab/homelab-llm`
- named volume for `/home/user`
- `OPEN_TERMINAL_ENABLE_TERMINAL=false`
- `OPEN_TERMINAL_ENABLE_NOTEBOOKS=false`
- image entrypoint creates compatibility symlinks before dropping back to
  `user`
- no `docker.sock`

## Path contract
- canonical repo root inside the container remains `/lab/homelab-llm`
- repo-relative paths such as `services/litellm-orch` remain the preferred form
- the derived image also accepts these compatibility aliases for the mounted
  repo root:
  - `/homelab-llm`
  - `/home/christopherbailey/homelab-llm`
- for top-level repo directories, the image also creates root-level aliases at
  container start when those paths are otherwise unused, for example:
  - `/services`
  - `/docs`
  - `/platform`
  - `/layer-interface`
- compatibility aliases are tolerated for `list_files.directory`,
  `read_file.path`, `grep_search.path`, and `glob_search.path`; canonical
  repo-relative paths are still the documented contract

## Upstream tool surface
Open Terminal `0.11.29` exposes:
- `health_check`
- `list_files`
- `read_file`
- `display_file`
- `write_file`
- `replace_file_content`
- `grep_search`
- `glob_search`
- `list_processes`
- `run_command`
- `get_process_status`
- `send_process_input`
- `kill_process`

## Current Open WebUI-exposed subset
Open WebUI currently registers this backend directly and only exposes:
- `health_check`
- `list_files`
- `read_file`
- `grep_search`
- `glob_search`

## Planned LiteLLM-exposed subset
If a shared LiteLLM MCP lane is added later, it should expose the same subset.

## Auth and policy
- Open Terminal MCP remains localhost-only and is not treated as the primary
  durable auth boundary.
- Backend bearer auth is enabled for defense in depth via
  `OPEN_TERMINAL_API_KEY`.
- In validation on the current `0.11.29` build, that key did not block
  anonymous MCP access on `/mcp`, so it is not relied on for this lane.
- Current Open WebUI connection therefore uses `auth_type=none` for the MCP
  backend and relies on localhost bind plus Open WebUI access control and tool
  filtering.
- A shared LiteLLM MCP alias is not part of the current live runtime.
- OpenHands worker keys remain denied for `/v1/mcp/*`.
