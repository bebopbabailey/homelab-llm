# Open WebUI (Mini) — Non-Docker Install

Open WebUI provides a local chat UI that talks to LiteLLM via OpenAI-compatible APIs.

## Install Location (Mini)
- App dir: `/home/christopherbailey/homelab-llm/layer-interface/open-webui` (legacy `/home/christopherbailey/open-webui` may exist)
- Data dir: `/home/christopherbailey/.open-webui`
- Env file: `/etc/open-webui/env`
- Systemd unit: `/etc/systemd/system/open-webui.service`

## Service (systemd)
```bash
systemctl status open-webui
sudo systemctl restart open-webui
```

## LiteLLM Upstream
Open WebUI uses OpenAI-compatible settings and plain model names from LiteLLM:
- `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`
- `OPENAI_API_KEY=dummy`

## Config Authority Warning
This deployment sets `ENABLE_PERSISTENT_CONFIG=False`.
Systemd env/drop-ins are authoritative across restarts, and Admin UI changes to
these values are non-persistent after restart.

## Web Search Ownership Boundary
- Open WebUI owns web-search UX plus provider/loader configuration.
- LiteLLM owns LLM routing and generic `/v1/search/<tool_name>` access only.
- vLLM owns inference and explicit structured decoding only when the caller requests it.

## Supported Open WebUI Web Search Settings
Use documented native Open WebUI settings from:
- `https://docs.openwebui.com/reference/env-configuration/`

Recommended Mini baseline:
- `WEB_SEARCH_ENGINE=searxng`
- `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`
- `WEB_SEARCH_RESULT_COUNT=6`
- `WEB_SEARCH_CONCURRENT_REQUESTS=1`
- `WEB_LOADER_ENGINE=safe_web`
- `WEB_LOADER_TIMEOUT=15`
- `WEB_LOADER_CONCURRENT_REQUESTS=2`
- `WEB_FETCH_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`
- `WEB_SEARCH_DOMAIN_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`

Do not point Open WebUI at `websearch-orch`, `EXTERNAL_WEB_LOADER_URL`, or any
LiteLLM prompt-shape/schema middleware for default web search.

## Model Notes
- `fast` is the default weaker local lane.
- `fast` does not imply agentic or schema-enforced web-search behavior.
- LiteLLM structured output support remains available only when the caller explicitly requests it.

## Generic LiteLLM Search Tool
LiteLLM still exposes `/v1/search/<tool_name>` for direct callers and MCP tools.
Current tool name is `searxng-search`.

Example request:
```bash
curl -X POST "http://127.0.0.1:4000/v1/search/searxng-search" \
  -H "Authorization: Bearer dummy" \
  -H "Content-Type: application/json" \
  -d '{"query":"openvino llm server","max_results":5}'
```

## Migration Note
The old custom path was intentionally removed:
- no LiteLLM web-search schema guardrail
- no prompt-shape coupling to legacy source tags
- no `websearch-orch` middle service in the supported Open WebUI path

## Install Notes
- The Open WebUI docs describe non-Docker installs using Python virtual environments.

## Access
Open WebUI listens on `http://<mini-host>:3000` by default.

## Resource Notes
- The UI service itself is CPU/RAM bound and does not use the Mini's GPU.
- Inference is performed by LiteLLM backends (Studio MLX + Mini OpenVINO).
- If you enable Open WebUI features like embeddings or OCR, it will use more CPU/RAM and local storage.
