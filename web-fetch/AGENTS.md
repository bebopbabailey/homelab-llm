# Agent Guidance: Web Fetch MCP Tool

## Scope
Keep as a local stdio tool. No systemd unit unless explicitly approved.

## Run
```bash
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
uv venv .venv
uv pip install -e .
web-fetch-mcp
```
