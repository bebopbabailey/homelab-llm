# 2026-03-25 — Open Terminal MCP reality snapshot

## Scope
Terminal-focused evidence snapshot for the Mini after the Open Terminal MCP
read-only slice was brought up behind LiteLLM.

## Runtime facts
- Native Open Terminal API is listening on `127.0.0.1:8010`.
- Open Terminal MCP is listening on `127.0.0.1:8011/mcp`.
- LiteLLM exposes the namespaced read-only MCP lane
  `open_terminal_repo_ro-*`.
- OpenHands worker access to `/v1/mcp/tools` remains denied with `403`.
- The runtime MCP registry exists at `/etc/homelab-llm/mcp-registry.json`
  and still needed reconciliation with the repo template during this sweep.

## Evidence commands
```bash
ss -ltnp | rg ':8010 |:8011 '

curl -i -sS http://127.0.0.1:8011/mcp | sed -n '1,20p'

set -a
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
set +a
curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://127.0.0.1:4000/v1/mcp/tools | jq '.tools[] | select(.name|startswith("open_terminal_repo_ro-")) | .name'

OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)
curl -sS -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/mcp/tools \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}"
```

## Observed signals
- `GET /mcp` on `8011` returned `406 Not Acceptable`, which is the expected
  Streamable HTTP MCP handshake hint.
- LiteLLM returned exactly:
  - `open_terminal_repo_ro-health_check`
  - `open_terminal_repo_ro-list_files`
  - `open_terminal_repo_ro-read_file`
  - `open_terminal_repo_ro-grep_search`
  - `open_terminal_repo_ro-glob_search`
- OpenHands worker probe returned `403`.
