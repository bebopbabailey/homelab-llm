# Tools Layer Runbook

## SearXNG (Mini)
```bash
sudo systemctl restart searxng.service
journalctl -u searxng.service -n 200 --no-pager
curl -fsS "http://127.0.0.1:8888/search?q=ping&format=json" | jq .
```

## MCP stdio tools (Mini)
MCP tools are invoked by a client (no port). See:
- `layer-tools/mcp-tools/web-fetch`
- `docs/INTEGRATIONS.md`

