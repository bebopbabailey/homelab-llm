# TinyAgents MCP Smoke

This script calls the MCP stdio tools hosted by `services/web-fetch`.
It does not require TinyAgents itself and is used to validate MCP tooling.

## Run
```bash
cd /home/christopherbailey/homelab-llm/services/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 /home/christopherbailey/homelab-llm/services/tiny-agents/scripts/mcp_smoke.py --tool search.web
```

Fetch a URL:
```bash
.venv/bin/python3 /home/christopherbailey/homelab-llm/services/tiny-agents/scripts/mcp_smoke.py --tool web.fetch --url https://example.com
```
