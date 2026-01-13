# Topology and Endpoints

## Hosts
- Mac Mini (Ubuntu 24.04): LiteLLM, Open WebUI, OpenVINO, OptiLLM, SearXNG, Ollama.
- Mac Studio: MLX OpenAI servers.
- HP DietPi: Home Assistant.

## Ports and Endpoints (authoritative)
Ports are immutable unless a migration is explicitly planned.
Do not change port allocations without updating `docs/PLATFORM_DOSSIER.md`.

| service | host | port | base URL | health |
| --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness |
| Open WebUI | Mini | 3000 | http://192.168.1.71:3000 | /health |
| OpenVINO LLM | Mini | 9000 | http://127.0.0.1:9000 | /health |
| OptiLLM proxy | Mini | 4020 | http://127.0.0.1:4020/v1 | /v1/models |
| SearXNG | Mini | 8888 | http://127.0.0.1:8888 | not documented |
| MLX (jerry-xl) | Studio | 8100 | http://192.168.1.72:8100/v1 | /v1/models |
| MLX (jerry-l) | Studio | 8101 | http://192.168.1.72:8101/v1 | /v1/models |
| MLX (jerry-m) | Studio | 8102 | http://192.168.1.72:8102/v1 | /v1/models |
| MLX (jerry-s) | Studio | 8103 | http://192.168.1.72:8103/v1 | /v1/models |
| MLX (bench-xl) | Studio | 8104 | http://192.168.1.72:8104/v1 | /v1/models |
| MLX (bench-l) | Studio | 8105 | http://192.168.1.72:8105/v1 | /v1/models |
| MLX (bench-m) | Studio | 8106 | http://192.168.1.72:8106/v1 | /v1/models |
| MLX (bench-s) | Studio | 8107 | http://192.168.1.72:8107/v1 | /v1/models |
| MLX (utility-a) | Studio | 8108 | http://192.168.1.72:8108/v1 | /v1/models |
| MLX (utility-b) | Studio | 8109 | http://192.168.1.72:8109/v1 | /v1/models |
| Ollama | Mini | 11434 | http://192.168.1.71:11434 | not documented |
| Home Assistant | DietPi | 8123 | http://192.168.1.70:8123 | not documented |

### MLX port management
- Ports 8100-8109 are reserved on the Studio and managed via `ops/scripts/mlxctl`.

## MCP Tools (stdio, no ports)
- `web.fetch` — stdio MCP tool on the Mini (no network port).
- `search.web` — stdio MCP tool that calls LiteLLM `/v1/search`, backed by SearXNG.

## Exposure and Secrets
- LAN-exposed: LiteLLM 4000, Open WebUI 3000, OpenVINO 9000 (maintenance), Ollama 11434,
  MLX 8100-8109, Home Assistant 8123.
- Local-only: OptiLLM 4020 (must not be LAN-exposed), SearXNG 8888.
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Env/secrets live outside the repo:
  - LiteLLM: `services/litellm-orch/config/env.local`
  - Open WebUI: `/etc/open-webui/env`
  - OpenVINO: `/etc/homelab-llm/ov-server.env`
  - SearXNG: `/etc/searxng/env`
