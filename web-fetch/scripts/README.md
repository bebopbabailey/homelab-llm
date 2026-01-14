# Web Fetch Demo Client

This script calls the `web.fetch` MCP tool over stdio and prints the result.

## Run
```bash
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 scripts/demo_client.py
```

Print clean text only:
```bash
.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text
```

Call search via MCP:
```bash
.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3
```
