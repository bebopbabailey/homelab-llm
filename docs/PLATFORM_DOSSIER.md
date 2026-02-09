# PLATFORM_DOSSIER

## Topology (current)
- Mac Mini: LiteLLM :4000 (localhost-only), Open WebUI :3000 (localhost-only),
  Prometheus :9090 (localhost-only), Grafana :3001 (localhost-only),
  OpenVINO :9000 (LAN-exposed for maintenance),
  SearXNG :8888 (localhost-only), Ollama :11434
- Mac Studio: MLX OpenAI servers :8100-:8119 (mlx-* team); :8120-:8139 reserved for experimental tests.
  Current default boot ensemble: 8100/8101/8102.
  OptiLLM proxy :4020 (localhost-only; used via LiteLLM `boost`).
- HP DietPi: Home Assistant :8123
## Topology (planned)
- Mac Studio: AFM (Apple Foundation Models) OpenAI-compatible API (target: :9999), routed via LiteLLM.

## Ports and endpoints (authoritative)

| service | host | port | bind | base URL | health | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | 127.0.0.1 | http://127.0.0.1:4000 | /health, /health/readiness, /health/liveliness | `/etc/systemd/system/litellm-orch.service`, `/proc/net/fib_trie` |
| Open WebUI | Mini | 3000 | 127.0.0.1 | http://127.0.0.1:3000 | /health | `/etc/systemd/system/open-webui.service`, `curl http://127.0.0.1:3000/health` |
| Prometheus | Mini | 9090 | 127.0.0.1 | http://127.0.0.1:9090 | /-/ready, /-/healthy | `/usr/lib/systemd/system/prometheus.service`, `/etc/default/prometheus` |
| Grafana | Mini | 3001 | 127.0.0.1 | http://127.0.0.1:3001 | /api/health | `/usr/lib/systemd/system/grafana-server.service`, `/etc/default/grafana-server` |
| OpenVINO LLM | Mini | 9000 | 0.0.0.0 | http://127.0.0.1:9000 | /health | `/etc/systemd/system/ov-server.service`, `/etc/homelab-llm/ov-server.env` |
| OptiLLM proxy | Studio | 4020 | 0.0.0.0 | http://192.168.1.72:4020/v1 | /v1/models | `layer-gateway/optillm-proxy` (deploy doc + unit), `router.yaml` `boost` |
| OptiLLM local (Orin) | Orin | 4040 | 0.0.0.0 | http://<orin-ip>:4040/v1 | /v1/models | service contract (active), systemd on Orin |
| SearXNG | Mini | 8888 | 127.0.0.1 | http://127.0.0.1:8888 | not documented | `/etc/systemd/system/searxng.service`, `/etc/searxng/settings.yml` |
| MLX (mlx-gpt-oss-120b-mxfp4-q4) | Studio | 8100 | 0.0.0.0 | http://192.168.1.72:8100/v1 | /v1/models | `/opt/mlx-launch/bin/start.sh`, registry |
| MLX (mlx-qwen3-next-80b-mxfp4-a3b-instruct) | Studio | 8101 | 0.0.0.0 | http://192.168.1.72:8101/v1 | /v1/models | `/opt/mlx-launch/bin/start.sh`, registry |
| MLX (mlx-gpt-oss-20b-mxfp4-q4) | Studio | 8102 | 0.0.0.0 | http://192.168.1.72:8102/v1 | /v1/models | `/opt/mlx-launch/bin/start.sh`, registry |
| AFM (planned) | Studio | 9999 | 0.0.0.0 | http://192.168.1.72:9999/v1 | /v1/models | owner confirmation (not yet wired) |
| Ollama | Mini | 11434 | 0.0.0.0 | http://192.168.1.71:11434 | not documented | `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf` |
| Home Assistant | DietPi | 8123 | 0.0.0.0 (assumed) | http://192.168.1.70:8123 | not documented | `/home/christopherbailey/.ssh/config`, owner confirmation |

### Port immutability
- Do not change or reuse ports without an explicit port-migration phase.

## Service inventory (concise)
- LiteLLM: systemd unit `/etc/systemd/system/litellm-orch.service`, json logs in `layer-gateway/litellm-orch/config/router.yaml`.
  Auth: API calls require `Authorization: Bearer <LITELLM_MASTER_KEY>` (even on localhost).
  Prometheus metrics: `/metrics/` (same port, auth required; use trailing slash).
- Prometheus: systemd unit `/usr/lib/systemd/system/prometheus.service`, config `/etc/homelab-llm/prometheus/prometheus.yml`.
- Grafana: systemd unit `/usr/lib/systemd/system/grafana-server.service`, config `/etc/homelab-llm/grafana/grafana.ini`,
  provisioning `/etc/homelab-llm/grafana/provisioning/`.
- Open WebUI: systemd unit `/etc/systemd/system/open-webui.service`, env `/etc/open-webui/env`, data `/home/christopherbailey/.open-webui`.
  Working dir: `/home/christopherbailey/homelab-llm/layer-interface/open-webui` (legacy `/home/christopherbailey/open-webui` may exist).
- OpenVINO: systemd unit `/etc/systemd/system/ov-server.service`, env `/etc/homelab-llm/ov-server.env`.
  OpenVINO is currently available as a standalone backend and is not wired as active LiteLLM handles.
  int4 on GPU is unstable (kernel compile failure); CPU-only int4 is possible but lower fidelity.
  Current env: `OV_DEVICE=GPU`, `OV_MODEL_PATH` fallback is fp32 (historical; registry is used for OpenVINO).
  Next evaluation: `OV_DEVICE=AUTO` and `OV_DEVICE=MULTI:GPU,CPU` for multi-request throughput.
- OptiLLM proxy (Studio): currently running as a user-managed process on the Studio.
  Evidence: `ps` shows `optillm --host 0.0.0.0 --port 4020 --approach router`.
  Upstream: MLX (current base URL points at `http://192.168.1.72:8101/v1`).
  LiteLLM routes to it via the `boost` handle (`OPTILLM_API_BASE` in `router.yaml`).
- OptiLLM local inference is **active** on Orin AGX (CUDA) via systemd.
  Studio has no opti-local runtime enabled.
  Note: Orin uses a startup patch (`PYTHONPATH` → `runtime/`) to disable sklearn
  imports on Jetson (`OPTILLM_DISABLE_SKLEARN=1`).
- SearXNG: systemd unit `/etc/systemd/system/searxng.service`, env `/etc/searxng/env`, localhost-only.
- MLX: ports 8100-8119 are team slots managed via `platform/ops/scripts/mlxctl`; 8120-8139 reserved for experimental tests.
  Current default boot ensemble: `8100` (gpt-oss-120b), `8101` (qwen3-next-80b), `8102` (gpt-oss-20b).
- MLX registry (`/Users/thestudio/models/hf/hub/registry.json`) maps canonical `model_id`
  to `source_path`/`cache_path` for inference.
  Only models present on Mini/Studio are exposed as LiteLLM handles (Seagate is backroom).
  Launchd plist `/Library/LaunchDaemons/com.bebop.mlx-launch.plist`, runtime `/opt/mlx-launch`.
- Ollama: systemd unit `/etc/systemd/system/ollama.service`.
- Home Assistant: OS package on DietPi, systemd-managed, root-run (owner confirmation).
- MCP tools: stdio tools (no ports) invoked by an MCP client; `web.fetch` and
  `search.web` are implemented, registry/systemd still pending.
- AFM: Apple Foundation Models OpenAI-compatible API (planned). Will be routed via LiteLLM.

## Data registries (authoritative)
- Lexicon registry (term correction): `layer-data/registry/lexicon.jsonl`

## Exposure and secrets (short)
- LAN-exposed: OpenVINO 9000 (maintenance), Ollama 11434,
  MLX 8100-8119, Home Assistant 8123, AFM 9999 (planned).
- Local-only: LiteLLM 4000 (tailnet HTTPS), Open WebUI 3000 (tailnet HTTPS),
  Prometheus 9090, Grafana 3001, SearXNG 8888.
- Tailnet HTTPS (Tailscale Serve on Mini):
  - `https://code.tailfd1400.ts.net/` → code-server (8080)
  - `https://chat.tailfd1400.ts.net/` → Open WebUI (3000)
  - `https://gateway.tailfd1400.ts.net/` → LiteLLM (4000)
  - `https://search.tailfd1400.ts.net/` → SearXNG (8888)
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Secrets/envs: `config/env.local`, `/etc/open-webui/env`, `/etc/homelab-llm/ov-server.env`, `/etc/searxng/env`.
- Tailscale ACLs/grants managed in admin (use `svc:*` grants for Services access).

## Decisions (ADR-lite)
- LiteLLM is the single gateway.
- Plain logical model names for clients.
- Ports treated as immutable.
