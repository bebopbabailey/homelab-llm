# Runbook: Open Terminal MCP

## Build image
```bash
docker build -t local/open-terminal-mcp:0.11.29 \
  -f /home/christopherbailey/homelab-llm/layer-tools/open-terminal/Dockerfile.mcp \
  /home/christopherbailey/homelab-llm
```

## Install env
```bash
sudo install -d -m 0755 /etc/open-terminal-mcp
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/templates/open-terminal-mcp.env.example \
  /etc/open-terminal-mcp/env
```

## Install service
```bash
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/systemd/open-terminal-mcp.service \
  /etc/systemd/system/open-terminal-mcp.service
sudo systemctl daemon-reload
sudo systemctl enable --now open-terminal-mcp.service
```

## Logs
```bash
journalctl -u open-terminal-mcp.service -n 200 --no-pager
docker logs --tail 200 open-terminal-mcp
```

## Direct MCP smoke
```bash
layer-interface/open-webui/.venv/bin/python - <<'PY'
import asyncio
from open_webui.utils.mcp.client import MCPClient

async def main():
    client = MCPClient()
    await client.connect("http://127.0.0.1:8011/mcp")
    tools = await client.list_tool_specs()
    print(sorted(tool["name"] for tool in tools))
    await client.disconnect()

asyncio.run(main())
PY
```

Expected:
- connect succeeds
- the raw upstream tool list includes the 13 Open Terminal tools
- this direct backend remains localhost-only

## Open WebUI direct registration smoke
```bash
python3 - <<'PY'
import sqlite3, json, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
headers = {'Authorization': f'Bearer {api_key}'}
for path in ['api/v1/terminals/', 'api/v1/tools/']:
    req = urllib.request.Request(f'http://127.0.0.1:3000/{path}', headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(path, resp.read().decode())
PY
```

Expected:
- `/api/v1/terminals/` lists `open-terminal`
- `/api/v1/tools/` lists `server:mcp:open-terminal-mcp-ro`
- the MCP tool lane is filtered to `health_check`, `list_files`, `read_file`,
  `grep_search`, and `glob_search`

## LiteLLM note
Shared LiteLLM exposure for the Open Terminal read-only subset is follow-on
work and is not part of the current live runtime. Validate the direct backend
and the direct Open WebUI registration only in this slice.

## Rollback
```bash
sudo systemctl disable --now open-terminal-mcp.service
sudo rm -f /etc/systemd/system/open-terminal-mcp.service
sudo systemctl daemon-reload
docker rm -f open-terminal-mcp || true
docker image rm local/open-terminal-mcp:0.11.29 || true
```
