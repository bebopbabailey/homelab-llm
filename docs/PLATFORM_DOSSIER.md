# PLATFORM_DOSSIER

## Topology (current)
- Mac Mini: LiteLLM :4000, Open WebUI :3000, OpenVINO :9000, Ollama :11434
- Mac Studio: MLX OpenAI servers :8100/:8101/:8102/:8103/:8109
- HP DietPi: Home Assistant :8123

## Ports and endpoints (authoritative)

| service | host | port | bind | base URL | health | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | 0.0.0.0 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness | `/etc/systemd/system/litellm-orch.service`, `/proc/net/fib_trie` |
| Open WebUI | Mini | 3000 | 0.0.0.0 | http://192.168.1.71:3000 | /health | `/etc/systemd/system/open-webui.service`, `curl http://127.0.0.1:3000/health` |
| OpenVINO LLM | Mini | 9000 | 0.0.0.0 | http://localhost:9000 | /health | `/home/christopherbailey/.config/systemd/user/ov-server.service`, `/home/christopherbailey/ov-llm-server/main.py` |
| MLX (jerry-chat) | Studio | 8100 | 0.0.0.0 | http://192.168.1.72:8100/v1 | /v1/models | `/home/christopherbailey/litellm-orch/config/env.local`, owner confirmation |
| MLX (jerry-editor) | Studio | 8101 | 0.0.0.0 | http://192.168.1.72:8101/v1 | /v1/models | `/home/christopherbailey/litellm-orch/config/env.local`, owner confirmation |
| MLX (jerry-architect) | Studio | 8102 | 0.0.0.0 | http://192.168.1.72:8102/v1 | /v1/models | `/home/christopherbailey/litellm-orch/config/env.local`, owner confirmation |
| MLX (jerry-weak) | Studio | 8103 | 0.0.0.0 | http://192.168.1.72:8103/v1 | /v1/models | `/home/christopherbailey/litellm-orch/config/env.local`, owner confirmation |
| MLX (jerry-test) | Studio | 8109 | 0.0.0.0 | http://192.168.1.72:8109/v1 | /v1/models | `/home/christopherbailey/litellm-orch/config/env.local`, owner confirmation |
| Ollama | Mini | 11434 | 0.0.0.0 | http://192.168.1.71:11434 | not documented | `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf` |
| Home Assistant | DietPi | 8123 | 0.0.0.0 (assumed) | http://192.168.1.70:8123 | not documented | `/home/christopherbailey/.ssh/config`, owner confirmation |

### Port immutability
- Do not change or reuse ports without an explicit port-migration phase.

## Service inventory (concise)
- LiteLLM: systemd unit `/etc/systemd/system/litellm-orch.service`, json logs in `config/router.yaml`.
- Open WebUI: systemd unit `/etc/systemd/system/open-webui.service`, env `/etc/open-webui/env`, data `/home/christopherbailey/.open-webui`.
- OpenVINO: user systemd unit `/home/christopherbailey/.config/systemd/user/ov-server.service`.
- MLX: scripts under `/home/christopherbailey/litellm-orch/scripts`, launchd plist `/Library/LaunchDaemons/com.bebop.mlx-launch.plist`, runtime `/opt/mlx-launch`.
- Ollama: systemd unit `/etc/systemd/system/ollama.service`.
- Home Assistant: OS package on DietPi, systemd-managed, root-run (owner confirmation).

## Exposure and secrets (short)
- LAN-exposed: LiteLLM 4000, Open WebUI 3000, OpenVINO 9000, Ollama 11434, MLX 8100-8103/8109, Home Assistant 8123.
- OpenVINO binds 0.0.0.0 for maintenance (owner confirmed).
- Secrets/envs: `config/env.local`, `/etc/open-webui/env`, `/home/christopherbailey/.config/ov-llm-server/ov-server.env`.
- Tailscale ACLs managed in admin (details not documented).

## Decisions (ADR-lite)
- LiteLLM is the single gateway.
- Plain logical model names for clients.
- Ports treated as immutable.
