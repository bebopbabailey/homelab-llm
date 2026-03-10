# PLATFORM_DOSSIER

## Topology (current)
- Mac Mini: LiteLLM :4000 (LAN + tailnet), Open WebUI :3000 (LAN + tailnet),
  Prometheus :9090 (localhost-only), Grafana :3001 (localhost-only),
  OpenVINO :9000 (LAN-exposed for maintenance),
  SearXNG :8888 (localhost-only), Ollama :11434
- Mac Studio: MLX inference host using per-lane launchd labels
  (`com.bebop.mlx-lane.8100/.8101/.8102`) with `vllm-metal`
  runtime listeners on `:8100/:8101/:8102`.
  OptiLLM proxy :4020 (active LiteLLM `boost` + `boost-deep` path).
  Studio main vector-store services (localhost-only): Postgres+pgvector `:55432`,
  memory API `:55440`, nightly ingest/backup jobs.
- Jetson Orin AGX: designated Voice Gateway host and future edge-experiment host.
  Current host identity and runtime status are canonical in `docs/foundation/orin-agx.md`.
  No inference backends are currently deployed.
- HP DietPi: Home Assistant :8123
## Topology (planned)
- Mac Studio: AFM (Apple Foundation Models) OpenAI-compatible API (target: :9999), routed via LiteLLM.

## Ports and endpoints (authoritative)

| service | host | port | bind | base URL | health | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | 0.0.0.0 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness | `/etc/systemd/system/litellm-orch.service`, `systemctl show litellm-orch.service -p ExecStart`, `ss -ltnp` |
| Open WebUI | Mini | 3000 | 0.0.0.0 | http://192.168.1.71:3000 | /health | `/etc/systemd/system/open-webui.service`, `systemctl show open-webui.service -p ExecStart`, `ss -ltnp` |
| Prometheus | Mini | 9090 | 127.0.0.1 | http://127.0.0.1:9090 | /-/ready, /-/healthy | `/usr/lib/systemd/system/prometheus.service`, `/etc/default/prometheus` |
| Grafana | Mini | 3001 | 127.0.0.1 | http://127.0.0.1:3001 | /api/health | `/usr/lib/systemd/system/grafana-server.service`, `/etc/default/grafana-server` |
| OpenVINO LLM | Mini | 9000 | 0.0.0.0 | http://127.0.0.1:9000 | /health | `/etc/systemd/system/ov-server.service`, `/etc/homelab-llm/ov-server.env` |
| OptiLLM proxy | Studio | 4020 | 0.0.0.0 | http://192.168.1.72:4020/v1 | /v1/models | `layer-gateway/optillm-proxy`, LiteLLM `boost`/`boost-deep` in `router.yaml` |
| Studio main vector DB | Studio | 55432 | 127.0.0.1 | http://127.0.0.1:55432 | n/a | `com.bebop.pgvector-main`, policy-managed launchd |
| Studio main memory API | Studio | 55440 | 127.0.0.1 | http://127.0.0.1:55440 | /health | `com.bebop.memory-api-main`, policy-managed launchd |
| SearXNG | Mini | 8888 | 127.0.0.1 | http://127.0.0.1:8888 | not documented | `/etc/systemd/system/searxng.service`, `/etc/searxng/settings.yml` |
| MLX inference lanes (active) | Studio | 8100/8101/8102 | 0.0.0.0 | http://192.168.1.72:8100/v1 | /v1/models | `com.bebop.mlx-lane.8100/.8101/.8102`, runtime `vllm serve`, `mlxctl status` |
| AFM (planned) | Studio | 9999 | 0.0.0.0 | http://192.168.1.72:9999/v1 | /v1/models | owner confirmation (not yet wired) |
| Ollama | Mini | 11434 | 0.0.0.0 | http://192.168.1.71:11434 | not documented | `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf` |
| Home Assistant | DietPi | 8123 | 0.0.0.0 (assumed) | http://192.168.1.70:8123 | not documented | `/home/christopherbailey/.ssh/config`, owner confirmation |

### Port immutability
- Do not change or reuse ports without an explicit port-migration phase.

## Service inventory (concise)
- LiteLLM: systemd unit `/etc/systemd/system/litellm-orch.service`, json logs in `layer-gateway/litellm-orch/config/router.yaml`.
  Auth: API calls require `Authorization: Bearer <LITELLM_MASTER_KEY>` (even on localhost).
  Health/auth behavior: `/v1/*` and `/health` are auth-gated; `/health/readiness`,
  `/health/liveliness`, and `/metrics/` are currently open.
  Runtime lock baseline: `drop_params=true`, `fast -> main`.
  Prometheus metrics: `/metrics/` (same port; use trailing slash).
  Harmony normalization is canonical at this layer for GPT lanes (`deep`, `fast`,
  `boost`, `boost-deep`) with strict wire-tag detection.
  GPT lanes now preserve caller streaming intent by default (no forced `stream=false`).
- Prometheus: systemd unit `/usr/lib/systemd/system/prometheus.service`, config `/etc/homelab-llm/prometheus/prometheus.yml`.
- Grafana: systemd unit `/usr/lib/systemd/system/grafana-server.service`, config `/etc/homelab-llm/grafana/grafana.ini`,
  provisioning `/etc/homelab-llm/grafana/provisioning/`.
- Open WebUI: systemd unit `/etc/systemd/system/open-webui.service`, env `/etc/open-webui/env`, data `/home/christopherbailey/.open-webui`.
  Working dir: `/home/christopherbailey/homelab-llm/layer-interface/open-webui` (legacy `/home/christopherbailey/open-webui` may exist).
  Current web-search contract is the documented native path:
  `WEB_SEARCH_ENGINE=searxng`,
  `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`,
  `WEB_SEARCH_RESULT_COUNT=6`,
  `WEB_SEARCH_CONCURRENT_REQUESTS=1`,
  `WEB_LOADER_ENGINE=safe_web`,
  `WEB_LOADER_TIMEOUT=15`,
  `WEB_LOADER_CONCURRENT_REQUESTS=2`,
  `WEB_FETCH_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`,
  `WEB_SEARCH_DOMAIN_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`.
  `ENABLE_PERSISTENT_CONFIG=False` makes env/drop-ins authoritative; Admin UI changes are non-persistent after restart.
- OpenVINO: systemd unit `/etc/systemd/system/ov-server.service`, env `/etc/homelab-llm/ov-server.env`.
  OpenVINO is currently available as a standalone backend and is not wired as active LiteLLM handles.
  int4 on GPU is unstable (kernel compile failure); CPU-only int4 is possible but lower fidelity.
  Current env: `OV_DEVICE=GPU`, `OV_MODEL_PATH` fallback is fp32 (historical; registry is used for OpenVINO).
  Next evaluation: `OV_DEVICE=AUTO` and `OV_DEVICE=MULTI:GPU,CPU` for multi-request throughput.
- OptiLLM proxy (Studio): managed by launchd.
  Evidence: `/Library/LaunchDaemons/com.bebop.optillm-proxy.plist`.
  Runtime args include: `--host 0.0.0.0 --port 4020 --model main --base-url http://100.69.99.60:4443/v1`.
  Upstream: Mini LiteLLM via tailnet TCP forward (`100.69.99.60:4443 -> 127.0.0.1:4000`).
  LiteLLM routes `boost` to this proxy via `OPTILLM_API_BASE`.
  Deploy contract is exact-SHA from repo checkout with `uv sync --frozen`.
  Current package baseline is `optillm==0.3.12` from PyPI with no deploy-time patching.
  Trio canary (`boost-plan-trio`) uses the local `plansearchtrio` plugin.
- SearXNG: systemd unit `/etc/systemd/system/searxng.service`, env `/etc/searxng/env`, localhost-only.
- MLX: ports 8100-8119 are team slots managed via `platform/ops/scripts/mlxctl`; 8120-8139 are experimental test ports and do not require `mlxctl`.
  Current active inference listeners: `8100/8101/8102` (`vllm serve` under `com.bebop.mlx-lane.8100/.8101/.8102`).
- MLX registry (`/Users/thestudio/models/hf/hub/registry.json`) maps canonical `model_id`
  to `source_path`/`cache_path` for inference.
  Only models present on Mini/Studio are exposed as LiteLLM handles (Seagate is backroom).
  Current team-lane runtime command family is `vllm serve` (`vllm-metal`) under per-lane launchd labels.
  Runtime lock baseline: `VLLM_METAL_MEMORY_FRACTION=auto`, `--api-key`, `--no-async-scheduling`, paged attention off.
  `mlxctl` now compiles per-lane vLLM args from registry (including strict parser
  capability validation for auto-tool lanes). Current staged default enables
  auto-tool for `main` (`8101`) only.
  Scheduling policy contract (strict two-lane + fail-closed allowlist):
  `docs/foundation/studio-scheduling-policy.md`.
- Ollama: systemd unit `/etc/systemd/system/ollama.service`.
- Home Assistant: OS package on DietPi, systemd-managed, root-run (owner confirmation).
- MCP tools: stdio tools (no ports) invoked by an MCP client; `web.fetch` and
  `search.web` are implemented, registry/systemd still pending.
- AFM: Apple Foundation Models OpenAI-compatible API (planned). Will be routed via LiteLLM.
- Studio main vector store: Postgres+pgvector backend for general/personal memory.
  Runtime now supports internal backend selection (`MEMORY_BACKEND=legacy|haystack`)
  while preserving the same API contract (`/v1/memory/*`). Service remains
  Studio-local (no LAN exposure) with tool-mediated retrieval boundary.
  Canonical source lives in monorepo `layer-data/vector-db`; deploy sync keeps
  the current Studio runtime target at `/Users/thestudio/optillm-proxy/layer-data/vector-db`.

## Data registries (authoritative)
- Lexicon registry (term correction): `layer-data/registry/lexicon.jsonl`

## Exposure and secrets (short)
- LAN-exposed: OpenVINO 9000 (maintenance), Ollama 11434,
  LiteLLM 4000, Open WebUI 3000, MLX 8100-8119, OptiLLM 4020, Home Assistant 8123, AFM 9999 (planned).
- Local-only: Prometheus 9090, Grafana 3001, SearXNG 8888.
- Local-only (Studio): main vector DB 55432, memory API 55440.
- Tailnet HTTPS (Tailscale Serve on Mini):
  - `https://code.tailfd1400.ts.net/` → code-server (8080)
  - `https://chat.tailfd1400.ts.net/` → Open WebUI (3000)
  - `https://gateway.tailfd1400.ts.net/` → LiteLLM (4000)
  - `https://search.tailfd1400.ts.net/` → SearXNG (8888)
- Tailnet TCP forward (Mini):
  - `100.69.99.60:4443` → `127.0.0.1:4000` (used by Studio OptiLLM upstream path)
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Secrets/envs: `config/env.local`, `/etc/open-webui/env`, `/etc/homelab-llm/ov-server.env`, `/etc/searxng/env`.
- Tailscale ACLs/grants managed in admin (use `svc:*` grants for Services access).

## Decisions (ADR-lite)
- LiteLLM is the single gateway.
- Plain logical model names for clients.
- Ports treated as immutable.
