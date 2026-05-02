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
- tool list includes `media-fetch.web.quick`
- tool list includes `media-fetch.web.session.search`

## Direct transcript smoke
```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
.venv/bin/python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = "https://youtu.be/-QFHIoCo-Ko?si=EP5WGz2PLVLPWU9j"

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("youtube.transcript", {"url": URL})
            assert not result.isError
            payload = json.loads(result.content[0].text)
            print(payload["video_id"], payload["language"], payload["caption_type"])
            print("segments", len(payload["segments"]))
            print("prefix", payload["transcript_text"][:120])

asyncio.run(main())
PY
```

Expected:
- `segments` is non-zero
- `transcript_text` is non-empty
- payload includes `source_url` and `language_code`

## Direct web search smoke
```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
.venv/bin/python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "media-fetch.web.search",
                {"query": "Open WebUI SearXNG integration", "max_results": 3},
            )
            assert not result.isError
            payload = json.loads(result.content[0].text)
            print(payload["provider"], len(payload["results"]))
            print(payload["results"][0]["url"])

asyncio.run(main())
PY
```

Expected:
- provider is `searxng`
- at least one normalized result is returned

## Direct fetch smoke
```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
.venv/bin/python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = "https://docs.openwebui.com/features/web-search/"

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("media-fetch.web.fetch", {"url": URL})
            assert not result.isError
            payload = json.loads(result.content[0].text)
            print(payload["canonical_url"])
            print(payload["extractor_used"], payload["quality_label"])
            print(payload["clean_text"][:120])

asyncio.run(main())
PY
```

Expected:
- `clean_text` is non-empty
- payload includes `canonical_url`, `markdown`, `quality_label`, and
  `extractor_used`

## Direct research-session smoke
```bash
TOKEN="$(platform/ops/scripts/studio_run_utility.sh --host studio -- \
  'cat /Users/thestudio/data/memory-main/secrets/memory-api-write-token')"
export MEDIA_FETCH_VECTOR_DB_WRITE_BEARER_TOKEN="$TOKEN"

cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
.venv/bin/python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "media-fetch.web.quick",
                {"conversation_id": "smoke-web-1", "query": "Open WebUI SearXNG integration"},
            )
            assert not result.isError
            payload = json.loads(result.content[0].text)
            print(payload["document_id"], len(payload["evidence"]))
            cleanup = await session.call_tool("media-fetch.web.session.delete", {"conversation_id": "smoke-web-1"})
            assert not cleanup.isError
            print(json.loads(cleanup.content[0].text)["deleted_documents"])

asyncio.run(main())
PY
```

Expected:
- `document_id` is `research:smoke-web-1`
- `evidence` is non-empty
- delete succeeds after the smoke run

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
        "function_name_filter_list": "youtube.transcript,media-fetch.web.quick,media-fetch.web.fetch",
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
