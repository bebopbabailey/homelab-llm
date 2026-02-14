# Topology and Endpoints

## Hosts
- Mac Mini (Ubuntu 24.04): LiteLLM, Open WebUI, Prometheus, Grafana, OpenVINO, OptiLLM, SearXNG, Ollama.
- Mac Studio: MLX inference host (canonical OpenAI-compatible endpoint: `mlx-omni-server` on `:8100`).
- Mac Studio (planned): AFM OpenAI-compatible API endpoint.
- HP DietPi: Home Assistant.
- Jetson Orin AGX: inference backends (OptiLLM local) and future CV/STT/TTS services.

## Host Dossier (new-agent quickstart)
Each host entry: role, access path, source-of-truth docs, and safe validation commands.

### Mini (Ubuntu 24.04)
- Role: gateway + UI + search + orchestration.
- Access: local repo on Mini.
- Sources of truth: `docs/foundation/topology.md`, `docs/foundation/overview.md`, per-service `SERVICE_SPEC.md`.
- Safe checks: prefer `curl http://127.0.0.1:4000/health/readiness` (current deployment requires auth for `/health`).
  LiteLLM `boost` routes to Studio OptiLLM proxy (`:4020`).

### Studio (macOS)
- Role: MLX inference host.
- Access: `ssh studio`.
- Sources of truth: `docs/foundation/mlx-registry.md`.
- Safe checks: `mlxctl status`, `curl http://127.0.0.1:8100/v1/models`.

### Orin AGX
- Role: edge inference + performance experiments.
- Access: `ssh orin` (final name TBD).
- Sources of truth: `docs/foundation/orin-agx.md`.
- Storage offload mount: `/mnt/seagate` from Mini path
  `christopherbailey@192.168.1.71:/mnt/seagate/orin-offload` (sshfs automount).
- Safe checks: `findmnt /mnt/seagate -o TARGET,SOURCE,FSTYPE,OPTIONS`.

### OV LLM Server (Mini)
- Role: OpenVINO server on Mini.
- Sources of truth: `docs/foundation/ov-llm-server.md`.

## Ports and Endpoints (authoritative)
Ports are immutable unless a migration is explicitly planned.
Do not change port allocations without updating `docs/PLATFORM_DOSSIER.md`.

| service | host | port | base URL | health |
| --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | http://127.0.0.1:4000 | /health, /health/readiness, /health/liveliness |
| Open WebUI | Mini | 3000 | http://127.0.0.1:3000 | /health |
| Prometheus | Mini | 9090 | http://127.0.0.1:9090 | /-/ready, /-/healthy |
| Grafana | Mini | 3001 | http://127.0.0.1:3001 | /api/health |
| OpenVINO LLM | Mini | 9000 | http://127.0.0.1:9000 | /health |
| OptiLLM proxy (Studio) | Studio | 4020 | http://192.168.1.72:4020/v1 | /v1/models |
| OptiLLM local (Orin) | Orin | 4040 | http://192.168.1.93:4040/v1 | /v1/models |
| SearXNG | Mini | 8888 | http://127.0.0.1:8888 | not documented |
| MLX Omni (served by Omni; model selected by `model`) | Studio | 8100 | http://192.168.1.72:8100/v1 | /v1/models |
| AFM (planned) | Studio | 9999 | http://192.168.1.72:9999/v1 | /v1/models |
| Ollama | Mini | 11434 | http://192.168.1.71:11434 | not documented |
| Home Assistant | DietPi | 8123 | http://192.168.1.70:8123 | not documented |

### MLX port management
- Ports 8100-8119 are team slots on the Studio and managed via `platform/ops/scripts/mlxctl`.
- Ports 8120-8139 are reserved for experimental test loads and are not registered until a model is loaded.
- Canonical endpoint: `8100` (mlx-omni-server). Additional ports may be unused unless explicitly enabled.

Note: on the Studio, `GET /v1/models` may return a local snapshot path as the model `id`.
Use `mlxctl status` as the canonical “which mlx-* model is on which port” signal.

### OptiLLM local (status)
- OptiLLM local inference runs on Orin via systemd (service contract in repo).
- Studio-local OptiLLM runtime serves LiteLLM `boost`.
- Orin offload storage is available at `/mnt/seagate` and persists across reboot via `/etc/fstab`.

## MCP Tools (stdio, no ports)
- `web.fetch` — stdio MCP tool on the Mini (no network port).
- `search.web` — stdio MCP tool that calls LiteLLM `/v1/search`, backed by SearXNG.

## Exposure and Secrets
- LAN-exposed: OpenVINO 9000 (maintenance), Ollama 11434,
  MLX 8100-8119, Home Assistant 8123, AFM 9999 (planned).
- Local-only: LiteLLM 4000 (tailnet HTTPS), Open WebUI 3000 (tailnet HTTPS),
  Prometheus 9090, Grafana 3001, SearXNG 8888.
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Env/secrets live outside the repo:
  - LiteLLM: `layer-gateway/litellm-orch/config/env.local`
  - Open WebUI: `/etc/open-webui/env`
  - OpenVINO: `/etc/homelab-llm/ov-server.env`
  - SearXNG: `/etc/searxng/env`
