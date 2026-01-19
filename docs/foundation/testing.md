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

Load a test model into the experimental range (8120+):
```bash
mlxctl load mlx-community/Qwen3-4B-Instruct-2507-gabliterated-mxfp4 auto
```

After any MLX port change:
```bash
mlxctl sync-gateway
```
```

## LiteLLM Aliases (Mini)
```bash
curl -fsS http://127.0.0.1:4000/v1/models | jq .
```

Check for MLX aliases:
```bash
curl -fsS http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | rg '^(mlx|ov|opt)-'
```

Check for OpenVINO aliases:
```bash
curl -fsS http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | rg '^ov-'
```

## OptiLLM (Mini)
```bash
curl -fsS http://127.0.0.1:4020/v1/models -H "Authorization: Bearer dummy" | jq .
```

## OptiLLM local (Studio)
```bash
curl -fsS http://192.168.1.72:4041/v1/models -H "Authorization: Bearer dummy" | jq .
```

Verify OptiLLM via LiteLLM alias (when handles are registered):
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"opt-router-<base-model>","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq .
```

Verify direct MLX handles (when models are registered):
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mlx-<base-model>","messages":[{"role":"user","content":"ping"}],"max_tokens":128}' \
  | jq .
```

## OpenVINO (Mini)
```bash
curl -fsS http://127.0.0.1:9000/health | jq .
```

## OpenVINO device mode evaluation (Mini)
Test latency and throughput with the same 1500-char input:
```bash
# GPU only (current)
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=GPU/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service

# AUTO
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=AUTO/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service

# MULTI CPU+GPU
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=MULTI:GPU,CPU/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service
```

## Non-LLM pilot tests (Mini)
Run and capture timing + quality notes:
```bash
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/onnx_eval.py
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/clean_punct_onnx.py
```

## STT/TTS/Vision evaluation (planned)
Track candidate models, ports, and benchmarks in `docs/journal/`.

## AFM (Studio, planned)
Once the AFM OpenAI-compatible API is running:
```bash
curl -fsS http://192.168.1.72:9999/v1/models | jq .
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
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text
```

## MCP search.web (Mini, stdio)
```bash
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3
```

## TinyAgents (Mini, once wired)
Run the agent with a known MCP tool and confirm tool output is reflected in the
response.

## MCP registry + TinyAgents env (MVP)
```bash
sudo cp /home/christopherbailey/homelab-llm/platform/ops/templates/mcp-registry.json /etc/homelab-llm/mcp-registry.json
sudo cp /home/christopherbailey/homelab-llm/platform/ops/templates/tiny-agents.env /etc/homelab-llm/tiny-agents.env
```

## OpenVINO model control (ovctl)
```bash
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl list
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl profiles
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl warm-profile ov-only-expanded
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl status
```

## ONNX evaluation (route + summarize)
```bash
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/onnx_eval.py
```
