# Open WebUI (Mini) — Non-Docker Install

Open WebUI provides a local chat UI that talks to LiteLLM via OpenAI-compatible APIs.

## Install Location (Mini)
- App dir: `/home/christopherbailey/homelab-llm/layer-interface/open-webui` (legacy `/home/christopherbailey/open-webui` may exist)
- Data dir: `/home/christopherbailey/.open-webui`
- Env file: `/etc/open-webui/env`
- Systemd unit: `/etc/systemd/system/open-webui.service`

## Service (systemd)
```
systemctl status open-webui
sudo systemctl restart open-webui
```

## LiteLLM Upstream
Open WebUI uses OpenAI-compatible settings and plain model names from LiteLLM:
- `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`
- `OPENAI_API_KEY=dummy`

This deployment sets `ENABLE_PERSISTENT_CONFIG=False`, so systemd env/drop-ins
remain authoritative across restarts.

## Web Search (active Open WebUI path)
Open WebUI is currently wired to `websearch-orch` for search + extraction:
- `SEARXNG_QUERY_URL=http://127.0.0.1:8899/search?q=<query>`
- `WEB_LOADER_ENGINE=external`
- `EXTERNAL_WEB_LOADER_URL=http://127.0.0.1:8899/web_loader`

LiteLLM also exposes `/v1/search/<tool_name>` for direct callers and MCP tools.
Current tool name is `searxng-search`.

Example request:
```bash
curl -X POST "http://127.0.0.1:4000/v1/search/searxng-search" \
  -H "Authorization: Bearer dummy" \
  -H "Content-Type: application/json" \
  -d '{"query":"openvino llm server","max_results":5}'
```

If Open WebUI is switched back to LiteLLM-native search, point it to the LiteLLM
base URL and use `/v1/search/searxng-search` as the endpoint.

## Install Notes
- The Open WebUI docs describe non-Docker installs using Python virtual environments.

## Access
Open WebUI listens on `http://<mini-host>:3000` by default.

## Resource Notes
- The UI service itself is CPU/RAM bound and does not use the Mini’s GPU.
- Inference is performed by LiteLLM backends (Studio MLX + Mini OpenVINO).
- If you enable Open WebUI features like embeddings or OCR, it will use more CPU/RAM and local storage.
