# Topology and Endpoints

## Hosts
- Mac Mini (Ubuntu 24.04): LiteLLM, Open WebUI, Prometheus, Grafana, OpenVINO, SearXNG, Ollama.
- Mac Studio: MLX inference host (per-lane launchd labels for `:8100/:8101/:8102` with `vllm-metal`), OptiLLM proxy (`:4020`), and Studio main vector-store services (localhost-only Postgres + memory API).
- Mac Studio (planned): AFM OpenAI-compatible API endpoint.
- HP DietPi: Home Assistant.
- Jetson Orin AGX: designated Voice Gateway host and future edge inference / performance experiments. Current runtime status is canonical in `docs/foundation/orin-agx.md`.

## Host Dossier (new-agent quickstart)
Each host entry: role, access path, source-of-truth docs, and safe validation commands.

### Mini (Ubuntu 24.04)
- Role: gateway + UI + search + orchestration.
- Access: local repo on Mini.
- Sources of truth: `docs/foundation/topology.md`, `docs/foundation/overview.md`, per-service `SERVICE_SPEC.md`.
- Safe checks: prefer `curl http://127.0.0.1:4000/health/readiness` (current deployment requires bearer auth for `/v1/*` and `/health`; readiness/liveliness and `/metrics/` are open).
  LiteLLM `boost` routes to Studio OptiLLM proxy (`:4020`).

### Studio (macOS)
- Role: MLX inference host.
- Access: `ssh studio`.
- Sources of truth: `docs/foundation/mlx-registry.md`, `docs/foundation/studio-scheduling-policy.md`.
- Safe checks: `mlxctl status`, `curl http://127.0.0.1:8100/v1/models`, `curl http://127.0.0.1:8101/v1/models`, `curl http://127.0.0.1:8102/v1/models`.
  Vector-store checks: `lsof -nP -iTCP -sTCP:LISTEN | egrep ':55432|:55440'`, `curl http://127.0.0.1:55440/health`.
  Vector-store labels are background-lane managed labels:
  `com.bebop.pgvector-main`, `com.bebop.memory-api-main`,
  `com.bebop.memory-ingest-nightly`, `com.bebop.memory-backup-nightly`.

### Orin AGX
- Role: designated Voice Gateway host + future edge inference / performance experiments.
- Access: `ssh orin` (SSH alias; see `docs/foundation/orin-agx.md` for host identity conventions).
- Sources of truth: `docs/foundation/orin-agx.md`.
- Safe checks: `findmnt /mnt/seagate -R -o TARGET,SOURCE,FSTYPE,OPTIONS`, `ss -ltnp`.

### OV LLM Server (Mini)
- Role: OpenVINO server on Mini.
- Sources of truth: `docs/foundation/ov-llm-server.md`.

## Ports and Endpoints (authoritative)
Ports are immutable unless a migration is explicitly planned.
Do not change port allocations without updating `docs/PLATFORM_DOSSIER.md`.

| service | host | port | base URL | health |
| --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness |
| Open WebUI | Mini | 3000 | http://192.168.1.71:3000 | /health |
| Prometheus | Mini | 9090 | http://127.0.0.1:9090 | /-/ready, /-/healthy |
| Grafana | Mini | 3001 | http://127.0.0.1:3001 | /api/health |
| OpenVINO LLM | Mini | 9000 | http://127.0.0.1:9000 | /health |
| OptiLLM proxy (Studio) | Studio | 4020 | http://192.168.1.72:4020/v1 | /v1/models |
| Studio main vector DB (postgres+pgvector) | Studio | 55432 | http://127.0.0.1:55432 | n/a |
| Studio main memory API | Studio | 55440 | http://127.0.0.1:55440 | /health |
| SearXNG | Mini | 8888 | http://127.0.0.1:8888 | not documented |
| MLX inference lanes (active) | Studio | 8100/8101/8102 | http://192.168.1.72:8100/v1 | /v1/models |
| AFM (planned) | Studio | 9999 | http://192.168.1.72:9999/v1 | /v1/models |
| Ollama | Mini | 11434 | http://192.168.1.71:11434 | not documented |
| Home Assistant | DietPi | 8123 | http://192.168.1.70:8123 | not documented |

### MLX port management
- Ports 8100-8119 are team slots on the Studio and managed via `platform/ops/scripts/mlxctl`.
- Ports 8120-8139 are reserved for experimental test loads; these ports do not require `mlxctl`.
- Current active inference listeners:
  - `8100`: `vllm serve` under `com.bebop.mlx-lane.8100`
  - `8101`: `vllm serve` under `com.bebop.mlx-lane.8101`
  - `8102`: `vllm serve` under `com.bebop.mlx-lane.8102`

Studio scheduling contract:
- inference lane labels: `com.bebop.mlx-lane.8100`, `com.bebop.mlx-lane.8101`, `com.bebop.mlx-lane.8102`, `com.bebop.optillm-proxy`
- non-inference transient automation runs with taskpolicy utility clamp
- strict allowlist policy for owned labels (`com.bebop.*`, `com.deploy.*`)
- details: `docs/foundation/studio-scheduling-policy.md`

Note: on the Studio, `GET /v1/models` may return a local snapshot path as the model `id`.
Use `mlxctl status` as the canonical “which mlx-* model is on which port” signal for `8100-8119`.

### OptiLLM local (status)
- No inference backends are currently deployed on Orin.
- Voice Gateway is designated for Orin, but a live deployment is not documented yet.
- Current Orin host state is canonical in `docs/foundation/orin-agx.md`; use the
  latest dated journal snapshot when checking volatile host details.
- Studio OptiLLM proxy serves LiteLLM `boost`.

## MCP Tools (stdio, no ports)
- `web.fetch` — stdio MCP tool on the Mini (no network port).
- `search.web` — stdio MCP tool that calls LiteLLM `/v1/search`, backed by SearXNG.

## Exposure and Secrets
- LAN-exposed: OpenVINO 9000 (maintenance), Ollama 11434,
  LiteLLM 4000, Open WebUI 3000, MLX 8100-8119, OptiLLM 4020, Home Assistant 8123, AFM 9999 (planned).
- Local-only: Prometheus 9090, Grafana 3001, SearXNG 8888.
  Studio local-only: main vector DB 55432, memory API 55440.
- Internal tailnet transport used by Studio OptiLLM upstream:
  - `100.69.99.60:4443` (Tailscale TCP forward on Mini -> `127.0.0.1:4000`)
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Env/secrets live outside the repo:
  - LiteLLM: `layer-gateway/litellm-orch/config/env.local`
  - Open WebUI: `/etc/open-webui/env`
  - OpenVINO: `/etc/homelab-llm/ov-server.env`
  - SearXNG: `/etc/searxng/env`

## Web Search Contract
- Open WebUI owns web-search UX plus provider/loader configuration.
- Current Mini deployment uses documented native Open WebUI settings:
  `WEB_SEARCH_ENGINE=searxng`,
  `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`,
  `WEB_SEARCH_RESULT_COUNT=6`,
  `WEB_SEARCH_CONCURRENT_REQUESTS=1`,
  `WEB_LOADER_ENGINE=safe_web`,
  `WEB_LOADER_TIMEOUT=15`,
  `WEB_LOADER_CONCURRENT_REQUESTS=2`,
  `WEB_FETCH_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`,
  `WEB_SEARCH_DOMAIN_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`.
- LiteLLM owns routing/auth/retries/fallbacks and generic `/v1/search/<tool_name>` access only.
- `websearch-orch` is not part of the supported runtime path.
