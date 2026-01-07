# 02-PORTS_ENDPOINTS_REGISTRY

Authoritative port and endpoint registry derived from current artifacts. Ports are treated as fixed unless a dedicated port-migration phase is explicitly defined later.

| service | host/machine | port | bind address | base URL | health endpoint | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| LiteLLM proxy (litellm-orch) | Mini | 4000 | 0.0.0.0 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness | `/etc/systemd/system/litellm-orch.service` (ExecStart --port 4000), `/home/christopherbailey/litellm-orch/SERVICE_SPEC.md`, `/proc/net/fib_trie` |
| Open WebUI | Mini | 3000 | 0.0.0.0 | http://192.168.1.71:3000 | /health | `/etc/systemd/system/open-webui.service`, `/home/christopherbailey/litellm-orch/docs/openwebui.md`, `/proc/net/fib_trie`, `curl http://127.0.0.1:3000/health` |
| OpenVINO LLM server (ov-llm-server) | Mini | 9000 | 0.0.0.0 | http://localhost:9000 | /health | `/home/christopherbailey/.config/systemd/user/ov-server.service`, `/home/christopherbailey/ov-llm-server/main.py` |
| MLX OpenAI server (jerry-chat) | Studio (per env) | 8100 | 0.0.0.0 | http://192.168.1.72:8100/v1 | /v1/models (reachability) | `/home/christopherbailey/litellm-orch/config/env.local`, `/home/christopherbailey/litellm-orch/scripts/run-mlx-gptoss-architect.sh`, `/home/christopherbailey/litellm-orch/TASKS.md`, user confirmation |
| MLX OpenAI server (jerry-editor) | Studio (per env) | 8101 | 0.0.0.0 | http://192.168.1.72:8101/v1 | /v1/models (reachability) | `/home/christopherbailey/litellm-orch/config/env.local`, `/home/christopherbailey/litellm-orch/scripts/run-mlx-studio.sh`, `/home/christopherbailey/litellm-orch/TASKS.md`, user confirmation |
| MLX OpenAI server (jerry-architect) | Studio (per env) | 8102 | 0.0.0.0 | http://192.168.1.72:8102/v1 | /v1/models (reachability) | `/home/christopherbailey/litellm-orch/config/env.local`, `/home/christopherbailey/litellm-orch/scripts/run-mlx-studio.sh`, `/home/christopherbailey/litellm-orch/TASKS.md`, user confirmation |
| MLX OpenAI server (jerry-weak) | Studio (per env) | 8103 | 0.0.0.0 | http://192.168.1.72:8103/v1 | /v1/models (reachability) | `/home/christopherbailey/litellm-orch/config/env.local`, `/home/christopherbailey/litellm-orch/scripts/run-mlx-studio.sh`, `/home/christopherbailey/litellm-orch/TASKS.md`, user confirmation |
| MLX OpenAI server (jerry-test) | Studio (per env) | 8109 | 0.0.0.0 | http://192.168.1.72:8109/v1 | /v1/models (reachability) | `/home/christopherbailey/litellm-orch/config/env.local`, `/home/christopherbailey/litellm-orch/scripts/run-mlx-test-model.sh`, `/home/christopherbailey/litellm-orch/TASKS.md`, user confirmation |
| Ollama | Mini | 11434 | 0.0.0.0 | http://192.168.1.71:11434 | health endpoint not documented (by design) | `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf`, `/proc/net/fib_trie`, user confirmation |
| Home Assistant (DietPi) | HP DietPi | 8123 | 0.0.0.0 (assumed) | http://192.168.1.70:8123 | health endpoint not documented | `/home/christopherbailey/.ssh/config`, user confirmation |

## Port immutability
- All ports above are treated as fixed. Do not change or reuse them without an explicit port-migration phase.
- New services must not bind to existing ports (4000, 3000, 9000, 8100-8103, 8109, 11434) unless a migration plan is documented and approved.
