# TinyAgents MCP Smoke

This script calls the MCP stdio tools hosted by `layer-tools/mcp-tools/web-fetch`.
It does not require TinyAgents itself and is used to validate MCP tooling.

## Run
```bash
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 /home/christopherbailey/homelab-llm/layer-gateway/tiny-agents/scripts/mcp_smoke.py --tool search.web
```

Fetch a URL:
```bash
.venv/bin/python3 /home/christopherbailey/homelab-llm/layer-gateway/tiny-agents/scripts/mcp_smoke.py --tool web.fetch --url https://example.com
```
