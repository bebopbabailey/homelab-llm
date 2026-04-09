# Tools Layer Runbook

## Prometheus (Mini)
```bash
sudo systemctl restart prometheus.service
journalctl -u prometheus.service -n 200 --no-pager
curl -fsS http://127.0.0.1:9090/-/ready
```

## SearXNG (Mini)
```bash
sudo systemctl restart searxng.service
journalctl -u searxng.service -n 200 --no-pager
curl -fsS "http://127.0.0.1:8888/search?q=ping&format=json" | jq .
```

## Open Terminal MCP (Mini)
```bash
sudo systemctl restart open-terminal-mcp.service
journalctl -u open-terminal-mcp.service -n 200 --no-pager
curl -i -sS http://127.0.0.1:8011/mcp | sed -n '1,20p'
```

Expected:
- service is active
- direct `GET /mcp` returns `406 Not Acceptable` unless the client accepts
  `text/event-stream`
- the current live path is the localhost direct backend, not a LiteLLM alias

## MCP stdio tools (Mini)
Registry-managed stdio tools are invoked by a client and do not bind a port.
