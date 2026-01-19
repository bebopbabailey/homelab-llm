# PLATFORM_DOSSIER

## Topology (current)
- Mac Mini: LiteLLM :4000, Open WebUI :3000, OpenVINO :9000 (LAN-exposed for maintenance),
  OptiLLM :4020 (localhost-only), SearXNG :8888 (localhost-only), Ollama :11434
- Mac Studio: MLX OpenAI servers :8100-:8119 (mlx-* team); :8120-:8139 reserved for experimental tests.
  Current default boot ensemble: 8100/8101/8102.
  OptiLLM local inference: :4040 (high), :4041 (balanced), :4042 reserved.
- HP DietPi: Home Assistant :8123
## Topology (planned)
- Mac Studio: AFM (Apple Foundation Models) OpenAI-compatible API (target: :9999), routed via LiteLLM.

## Ports and endpoints (authoritative)

| service | host | port | bind | base URL | health | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | 0.0.0.0 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness | `/etc/systemd/system/litellm-orch.service`, `/proc/net/fib_trie` |
| Open WebUI | Mini | 3000 | 0.0.0.0 | http://192.168.1.71:3000 | /health | `/etc/systemd/system/open-webui.service`, `curl http://127.0.0.1:3000/health` |
| OpenVINO LLM | Mini | 9000 | 0.0.0.0 | http://127.0.0.1:9000 | /health | `/etc/systemd/system/ov-server.service`, `/etc/homelab-llm/ov-server.env` |
| OptiLLM proxy | Mini | 4020 | 127.0.0.1 | http://127.0.0.1:4020/v1 | /v1/models | `layer-gateway/optillm-proxy/SERVICE_SPEC.md`, local install |
| OptiLLM local (high) | Studio | 4040 | 0.0.0.0 | http://192.168.1.72:4040/v1 | /v1/models | `layer-gateway/optillm-local/SERVICE_SPEC.md`, launchd |
| OptiLLM local (balanced) | Studio | 4041 | 0.0.0.0 | http://192.168.1.72:4041/v1 | /v1/models | `layer-gateway/optillm-local/SERVICE_SPEC.md`, launchd |
| SearXNG | Mini | 8888 | 127.0.0.1 | http://127.0.0.1:8888 | not documented | `/etc/systemd/system/searxng.service`, `/etc/searxng/settings.yml` |
| MLX (mlx-gpt-oss-120b-mxfp4-q4) | Studio | 8100 | 0.0.0.0 | http://192.168.1.72:8100/v1 | /v1/models | `/opt/mlx-launch/bin/start.sh`, registry |
| MLX (mlx-gemma-3-27b-it-qat-4bit) | Studio | 8101 | 0.0.0.0 | http://192.168.1.72:8101/v1 | /v1/models | `/opt/mlx-launch/bin/start.sh`, registry |
| MLX (mlx-gpt-oss-20b-mxfp4-q4) | Studio | 8102 | 0.0.0.0 | http://192.168.1.72:8102/v1 | /v1/models | `/opt/mlx-launch/bin/start.sh`, registry |
| AFM (planned) | Studio | 9999 | 0.0.0.0 | http://192.168.1.72:9999/v1 | /v1/models | owner confirmation (not yet wired) |
| Ollama | Mini | 11434 | 0.0.0.0 | http://192.168.1.71:11434 | not documented | `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf` |
| Home Assistant | DietPi | 8123 | 0.0.0.0 (assumed) | http://192.168.1.70:8123 | not documented | `/home/christopherbailey/.ssh/config`, owner confirmation |

### Port immutability
- Do not change or reuse ports without an explicit port-migration phase.

## Service inventory (concise)
- LiteLLM: systemd unit `/etc/systemd/system/litellm-orch.service`, json logs in `layer-gateway/litellm-orch/config/router.yaml`.
- Open WebUI: systemd unit `/etc/systemd/system/open-webui.service`, env `/etc/open-webui/env`, data `/home/christopherbailey/.open-webui`.
  Working dir: `/home/christopherbailey/homelab-llm/layer-interface/open-webui` (legacy `/home/christopherbailey/open-webui` may exist).
- OpenVINO: systemd unit `/etc/systemd/system/ov-server.service`, env `/etc/homelab-llm/ov-server.env`.
  LiteLLM now uses `ov-*` aliases that map directly to base OpenVINO model IDs; `ov-*` is deprecated.
  int4 on GPU is unstable (kernel compile failure); CPU-only int4 is possible but lower fidelity.
  Current env: `OV_DEVICE=GPU`, `OV_MODEL_PATH` fallback is fp32 (historical; registry is used for OpenVINO).
  Next evaluation: `OV_DEVICE=AUTO` and `OV_DEVICE=MULTI:GPU,CPU` for multi-request throughput.
- OptiLLM: systemd unit `/etc/systemd/system/optillm-proxy.service`, env `/etc/optillm-proxy/env`, localhost-only proxy.
- OptiLLM local (Studio): launchd units, HF cache `/Users/thestudio/models/hf/hub`, pin `transformers<5` for router.
  Local OptiLLM launchd is disabled by default until setup is finalized.
- SearXNG: systemd unit `/etc/systemd/system/searxng.service`, env `/etc/searxng/env`, localhost-only.
- MLX: ports 8100-8119 are team slots managed via `platform/ops/scripts/mlxctl`; 8120-8139 reserved for experimental tests.
  Current default boot ensemble: `8100` (gpt-oss-120b), `8101` (gemma-27b), `8102` (gpt-oss-20b).
- MLX registry (`/Users/thestudio/models/hf/hub/registry.json`) maps canonical `model_id`
  to `source_path`/`cache_path` for inference.
  Only models present on Mini/Studio are exposed as LiteLLM handles (Seagate is backroom).
  Launchd plist `/Library/LaunchDaemons/com.bebop.mlx-launch.plist`, runtime `/opt/mlx-launch`.
- Ollama: systemd unit `/etc/systemd/system/ollama.service`.
- Home Assistant: OS package on DietPi, systemd-managed, root-run (owner confirmation).
- MCP tools: stdio tools (no ports) invoked by an MCP client; `web.fetch` and
  `search.web` are implemented, registry/systemd still pending.
- AFM: Apple Foundation Models OpenAI-compatible API (planned). Will be routed via LiteLLM.

## Exposure and secrets (short)
- LAN-exposed: LiteLLM 4000, Open WebUI 3000, OpenVINO 9000 (maintenance), Ollama 11434,
  MLX 8100-8119, Home Assistant 8123, AFM 9999 (planned).
- Local-only: OptiLLM 4020, SearXNG 8888.
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Secrets/envs: `config/env.local`, `/etc/open-webui/env`, `/etc/homelab-llm/ov-server.env`, `/etc/searxng/env`.
- Tailscale ACLs managed in admin (details not documented).

## Decisions (ADR-lite)
- LiteLLM is the single gateway.
- Plain logical model names for clients.
- Ports treated as immutable.
