# Topology and Endpoints

## Hosts
- Mac Mini (Ubuntu 24.04): LiteLLM, Open WebUI, OpenVINO, Ollama.
- Mac Studio: MLX OpenAI servers.
- HP DietPi: Home Assistant.

## Ports and Endpoints (authoritative)
Ports are immutable unless a migration is explicitly planned.
Do not change port allocations without updating `docs/PLATFORM_DOSSIER.md`.

| service | host | port | base URL | health |
| --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness |
| Open WebUI | Mini | 3000 | http://192.168.1.71:3000 | /health |
| OpenVINO LLM | Mini | 9000 | http://localhost:9000 | /health |
| OptiLLM proxy | Mini | 4020 | http://127.0.0.1:4020/v1 | /v1/models |
| MLX (jerry-chat) | Studio | 8100 | http://192.168.1.72:8100/v1 | /v1/models |
| MLX (jerry-editor) | Studio | 8101 | http://192.168.1.72:8101/v1 | /v1/models |
| MLX (jerry-architect) | Studio | 8102 | http://192.168.1.72:8102/v1 | /v1/models |
| MLX (jerry-weak) | Studio | 8103 | http://192.168.1.72:8103/v1 | /v1/models |
| MLX (jerry-test) | Studio | 8109 | http://192.168.1.72:8109/v1 | /v1/models |
| Ollama | Mini | 11434 | http://192.168.1.71:11434 | not documented |
| Home Assistant | DietPi | 8123 | http://192.168.1.70:8123 | not documented |

## Exposure and Secrets
- LAN-exposed: LiteLLM 4000, Open WebUI 3000, OpenVINO 9000, Ollama 11434,
  MLX 8100-8103/8109, Home Assistant 8123.
- Local-only: OptiLLM 4020 (must not be LAN-exposed).
- Env/secrets live outside the repo:
  - LiteLLM: `services/litellm-orch/config/env.local`
  - Open WebUI: `/etc/open-webui/env`
  - OpenVINO: `/home/christopherbailey/.config/ov-llm-server/ov-server.env`
