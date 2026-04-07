# 2026-03-25 — Open Terminal MCP reality snapshot

## Scope
Terminal-focused evidence snapshot for the Mini after the localhost-only Open
Terminal MCP slice was brought up and compared against the planned shared
LiteLLM path.

## Runtime facts
- Native Open Terminal API is listening on `127.0.0.1:8010`.
- Open Terminal MCP is listening on `127.0.0.1:8011/mcp`.
- LiteLLM does not currently expose the planned namespaced read-only MCP lane.
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
  http://127.0.0.1:4000/v1/mcp/tools | jq .

OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)
curl -sS -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/mcp/tools \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}"
```

## Observed signals
- `GET /mcp` on `8011` returned `406 Not Acceptable`, which is the expected
  Streamable HTTP MCP handshake hint.
- LiteLLM MCP visibility did not include any planned read-only shared-lane
  tools in this snapshot; the shared read-only lane remained planned rather
  than live.
- OpenHands worker probe returned `403`.
