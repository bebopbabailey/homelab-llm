# Runbook: media-fetch-mcp

## Install env
```bash
sudo install -d -m 0755 /etc/homelab-llm
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/templates/media-fetch-mcp.env.example \
  /etc/homelab-llm/media-fetch-mcp.env
```

## Install service
```bash
sudo install -m 0644 \
  /home/christopherbailey/homelab-llm/platform/ops/systemd/media-fetch-mcp.service \
  /etc/systemd/system/media-fetch-mcp.service
sudo systemctl daemon-reload
sudo systemctl enable --now media-fetch-mcp.service
```

## Logs
```bash
journalctl -u media-fetch-mcp.service -n 200 --no-pager
```

## Direct MCP smoke
```bash
/home/christopherbailey/homelab-llm/services/open-webui/.venv/bin/python - <<'PY'
import asyncio
from open_webui.utils.mcp.client import MCPClient

async def main():
    client = MCPClient()
    await client.connect("http://127.0.0.1:8012/mcp")
    try:
        tools = await client.list_tool_specs()
        print(sorted(tool["name"] for tool in tools))
    finally:
        await client.disconnect()

asyncio.run(main())
PY
```

Expected:
- connect succeeds
- tool list includes `youtube.transcript`

## Open WebUI verify smoke
```bash
python3 - <<'PY'
import json, sqlite3, urllib.request

conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
payload = {
    "url": "http://127.0.0.1:8012/mcp",
    "path": "",
    "type": "mcp",
    "auth_type": "none",
    "key": "",
    "config": {
        "enable": True,
        "function_name_filter_list": "youtube.transcript",
        "access_grants": []
    },
    "info": {"id": "media-fetch-mcp", "name": "Media Fetch MCP"}
}
req = urllib.request.Request(
    'http://127.0.0.1:3000/api/v1/configs/tool_servers/verify',
    data=json.dumps(payload).encode(),
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
)
with urllib.request.urlopen(req, timeout=20) as resp:
    print(resp.read().decode())
PY
```

Expected:
- verify succeeds against `127.0.0.1:8012/mcp`

## Local tool smoke
```bash
curl -fsS http://127.0.0.1:8012/mcp >/dev/null
```

Expected:
- endpoint responds on localhost

## Rollback
```bash
sudo systemctl disable --now media-fetch-mcp.service
sudo rm -f /etc/systemd/system/media-fetch-mcp.service
sudo systemctl daemon-reload
```
