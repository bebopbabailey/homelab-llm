# PLATFORM_DOSSIER

## Topology (current)
- Mac Mini: LiteLLM :4000, Open WebUI :3000, OpenVINO :9000 (LAN-exposed for maintenance),
  OptiLLM :4020 (localhost-only), SearXNG :8888 (localhost-only), Ollama :11434
- Mac Studio: MLX OpenAI servers :8100-:8109 (jerry/bench/utility slots)
- HP DietPi: Home Assistant :8123
## Topology (planned)
- Mac Studio: AFM (Apple Foundation Models) OpenAI-compatible API (target: :9999), routed via LiteLLM.

## Ports and endpoints (authoritative)

| service | host | port | bind | base URL | health | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | 0.0.0.0 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness | `/etc/systemd/system/litellm-orch.service`, `/proc/net/fib_trie` |
| Open WebUI | Mini | 3000 | 0.0.0.0 | http://192.168.1.71:3000 | /health | `/etc/systemd/system/open-webui.service`, `curl http://127.0.0.1:3000/health` |
| OpenVINO LLM | Mini | 9000 | 0.0.0.0 | http://127.0.0.1:9000 | /health | `/etc/systemd/system/ov-server.service`, `/etc/homelab-llm/ov-server.env` |
| OptiLLM proxy | Mini | 4020 | 127.0.0.1 | http://127.0.0.1:4020/v1 | /v1/models | `services/optillm-proxy/SERVICE_SPEC.md`, local install |
| SearXNG | Mini | 8888 | 127.0.0.1 | http://127.0.0.1:8888 | not documented | `/etc/systemd/system/searxng.service`, `/etc/searxng/settings.yml` |
| MLX (jerry-xl) | Studio | 8100 | 0.0.0.0 | http://192.168.1.72:8100/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (jerry-l) | Studio | 8101 | 0.0.0.0 | http://192.168.1.72:8101/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (jerry-m) | Studio | 8102 | 0.0.0.0 | http://192.168.1.72:8102/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (jerry-s) | Studio | 8103 | 0.0.0.0 | http://192.168.1.72:8103/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (bench-xl) | Studio | 8104 | 0.0.0.0 | http://192.168.1.72:8104/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (bench-l) | Studio | 8105 | 0.0.0.0 | http://192.168.1.72:8105/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (bench-m) | Studio | 8106 | 0.0.0.0 | http://192.168.1.72:8106/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (bench-s) | Studio | 8107 | 0.0.0.0 | http://192.168.1.72:8107/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (utility-a) | Studio | 8108 | 0.0.0.0 | http://192.168.1.72:8108/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| MLX (utility-b) | Studio | 8109 | 0.0.0.0 | http://192.168.1.72:8109/v1 | /v1/models | `/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local`, owner confirmation |
| AFM (planned) | Studio | 9999 | 0.0.0.0 | http://192.168.1.72:9999/v1 | /v1/models | owner confirmation (not yet wired) |
| Ollama | Mini | 11434 | 0.0.0.0 | http://192.168.1.71:11434 | not documented | `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf` |
| Home Assistant | DietPi | 8123 | 0.0.0.0 (assumed) | http://192.168.1.70:8123 | not documented | `/home/christopherbailey/.ssh/config`, owner confirmation |

### Port immutability
- Do not change or reuse ports without an explicit port-migration phase.

## Service inventory (concise)
- LiteLLM: systemd unit `/etc/systemd/system/litellm-orch.service`, json logs in `services/litellm-orch/config/router.yaml`.
- Open WebUI: systemd unit `/etc/systemd/system/open-webui.service`, env `/etc/open-webui/env`, data `/home/christopherbailey/.open-webui`.
  Working dir: `/home/christopherbailey/homelab-llm/services/open-webui` (legacy `/home/christopherbailey/open-webui` may exist).
- OpenVINO: systemd unit `/etc/systemd/system/ov-server.service`, env `/etc/homelab-llm/ov-server.env`.
  Runtime uses int8 for `benny-clean-*` via LiteLLM; fp16 variants remain in the registry.
  int4 on GPU is unstable (kernel compile failure); CPU-only int4 is possible but lower fidelity.
  Current env: `OV_DEVICE=GPU`, `OV_MODEL_PATH` fallback is fp32 (historical; registry is used for Benny).
  Next evaluation: `OV_DEVICE=AUTO` and `OV_DEVICE=MULTI:GPU,CPU` for multi-request throughput.
- OptiLLM: systemd unit `/etc/systemd/system/optillm-proxy.service`, env `/etc/optillm-proxy/env`, localhost-only proxy.
- SearXNG: systemd unit `/etc/systemd/system/searxng.service`, env `/etc/searxng/env`, localhost-only.
- MLX: ports 8100-8109 are reserved and managed via `ops/scripts/mlxctl` on the Studio.
  Launchd plist `/Library/LaunchDaemons/com.bebop.mlx-launch.plist`, runtime `/opt/mlx-launch`.
- Ollama: systemd unit `/etc/systemd/system/ollama.service`.
- Home Assistant: OS package on DietPi, systemd-managed, root-run (owner confirmation).
- MCP tools: stdio tools (no ports) invoked by an MCP client; `web.fetch` and
  `search.web` are implemented, registry/systemd still pending.
- AFM: Apple Foundation Models OpenAI-compatible API (planned). Will be routed via LiteLLM.

## Exposure and secrets (short)
- LAN-exposed: LiteLLM 4000, Open WebUI 3000, OpenVINO 9000 (maintenance), Ollama 11434,
  MLX 8100-8109, Home Assistant 8123, AFM 9999 (planned).
- Local-only: OptiLLM 4020, SearXNG 8888.
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Secrets/envs: `config/env.local`, `/etc/open-webui/env`, `/etc/homelab-llm/ov-server.env`, `/etc/searxng/env`.
- Tailscale ACLs managed in admin (details not documented).

## Decisions (ADR-lite)
- LiteLLM is the single gateway.
- Plain logical model names for clients.
- Ports treated as immutable.
