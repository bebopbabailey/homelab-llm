# Testing and Verification

This doc captures the recommended test steps for new changes. Run these on the
appropriate host and confirm outputs before declaring a change complete.

## MLX Registry and Controller (Studio)
```bash
mlxctl init
mlxctl list
mlxctl status
```

Load and unload a model (example):
```bash
mlxctl load mlx-community/Qwen3-235B-A22B-Instruct-2507-6bit 8100
mlxctl status
mlxctl unload 8100
mlxctl status
```

Unload all ports:
```bash
mlxctl unload-all
```

Reconcile after reboot:
```bash
mlxctl reconcile
```

## MLX Launchd Boot Model (Studio)
After reboot or launchd restart, confirm port 8100 is serving Qwen3-235B:
```bash
curl -fsS http://127.0.0.1:8100/v1/models | jq .
```

## LiteLLM Aliases (Mini)
```bash
curl -fsS http://127.0.0.1:4000/v1/models | jq .
```

Check for MLX aliases:
```bash
curl -fsS http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | rg '^(jerry|bench|utility)-'
```

Check for OpenVINO aliases:
```bash
curl -fsS http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | rg '^benny-'
```

## OptiLLM (Mini)
```bash
curl -fsS http://127.0.0.1:4020/v1/models | jq .
```

## OpenVINO (Mini)
```bash
curl -fsS http://127.0.0.1:9000/health | jq .
```

## SearXNG (Mini, once installed)
```bash
curl -fsS "http://127.0.0.1:8888/search?q=ping&format=json" | jq .
```

## LiteLLM Search Proxy (Mini)
```bash
curl -fsS http://127.0.0.1:4000/v1/search/searxng-search \
  -H "Authorization: Bearer dummy" \
  -H "Content-Type: application/json" \
  -d '{"query":"openvino llm","max_results":3}' | jq .
```

## MCP web.fetch (Mini, stdio)
```bash
cd /home/christopherbailey/homelab-llm/services/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text
```

## MCP search.web (Mini, stdio)
```bash
cd /home/christopherbailey/homelab-llm/services/web-fetch
.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3
```

## TinyAgents (Mini, once wired)
Run the agent with a known MCP tool and confirm tool output is reflected in the
response.
