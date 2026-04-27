# Topology and Endpoints

## Hosts
- Mac Mini (Ubuntu 24.04): commodity gateway/control surface for LiteLLM, Open WebUI, OpenCode, OpenHands, Prometheus, Grafana, OpenVINO, SearXNG, Ollama, plus the localhost-only `orchestration-cockpit` prototype when launched.
- Mac Studio: public inference host for the `mlxctl`-governed team-lane domain on `:8100-:8119`, the shared `llmster` GPT listener on `:8126`, and the specialized runtime-plane host represented by `omlx-runtime`.
- Mac Studio (planned): AFM OpenAI-compatible API endpoint.
- Mac Studio: active shared `llmster` GPT service on `8126`, with public
  `fast` and `deep` both routed through `8126`. Shadow ports `8123-8125` are
  retired.
- HP DietPi: Home Assistant.
- Jetson Orin AGX: live canonical speech appliance host with LAN-visible `voice-gateway` and localhost-only Speaches behind it. Runtime evidence is canonical in `docs/foundation/orin-agx.md`.

## Host Dossier (new-agent quickstart)
Each host entry: role, access path, source-of-truth docs, and safe validation commands.

### Mini (Ubuntu 24.04)
- Role: commodity inference plane + UI + search + orchestration + LAN file sharing.
- Access: local repo on Mini.
- Sources of truth: `docs/foundation/topology.md`, `docs/foundation/overview.md`, per-service `SERVICE_SPEC.md`.
- Safe checks: prefer `curl http://127.0.0.1:4000/health/readiness` (current deployment requires bearer auth for `/v1/*` and `/health`; readiness/liveliness and `/metrics/` are open).
  LiteLLM `boost` routes to Studio OptiLLM proxy (`:4020`).
  OpenHands Phase A is systemd-managed on `127.0.0.1:4031` with tailnet-only
  operator access at `https://hands.tailfd1400.ts.net/`.
  OpenCode Web is on `127.0.0.1:4096` locally, uses HTTP Basic Auth, and is exposed on the tailnet at `https://codeagent.tailfd1400.ts.net/` via `svc:codeagent`.
  `orchestration-cockpit` is localhost-only and inactive by default; when
  launched it uses LangGraph dev on `127.0.0.1:2024` and Agent Chat UI on
  `127.0.0.1:3030`.
  Finder SMB is LAN-only on `127.0.0.1` + `192.168.1.71`, with authenticated shares `mini-root` and `seagate`.

### Studio (macOS)
- Role: public inference host plus specialized runtime-plane host.
- Access: `ssh studio`.
- Sources of truth: `docs/foundation/mlx-registry.md`, `docs/foundation/studio-scheduling-policy.md`.
- Safe checks: `mlxctl status`, `curl http://127.0.0.1:8101/v1/models`, `curl http://127.0.0.1:8126/v1/models`.
  Vector-store checks: `lsof -nP -iTCP -sTCP:LISTEN | egrep ':55432|:55440'`, `curl http://127.0.0.1:55440/health`.
  Vector-store labels are background-lane managed labels:
  `com.bebop.pgvector-main`, `com.bebop.memory-api-main`,
  `com.bebop.memory-ingest-nightly`, `com.bebop.memory-backup-nightly`.
- Current networking note: the canonical Mini -> Studio MLX path is the Studio
  LAN IP `192.168.1.72`; Tailscale hostnames are not part of the locked MLX lane
  transport contract.
  The specialized runtime plane is not assumed to share the same public gateway
  contract as the active `mlxctl` team lanes.

### Orin AGX
- Role: canonical speech appliance host + future edge inference / performance experiments.
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
| orchestration-cockpit (prototype, inactive by default) | Mini | 2024 / 3030 | http://127.0.0.1:2024, http://127.0.0.1:3030 | local dev only |
| CCProxy API (experimental, localhost-only) | Mini | 4010 | http://127.0.0.1:4010/codex/v1 | /codex/v1/models |
| Open Terminal API (human UX) | Mini | 8010 | http://127.0.0.1:8010 | /health |
| Open Terminal MCP | Mini | 8011 | http://127.0.0.1:8011/mcp | MCP handshake |
| OpenCode Web | Mini | 4096 | http://127.0.0.1:4096 | UI root (401 unauthenticated) |
| OpenHands (Phase A, managed operator UI) | Mini | 4031 | http://127.0.0.1:4031, https://hands.tailfd1400.ts.net/ | UI root |
| Samba SMB | Mini | 139/445 | smb://192.168.1.71/mini-root, smb://192.168.1.71/seagate | `testparm -s`, Finder auth |
| Prometheus | Mini | 9090 | http://127.0.0.1:9090 | /-/ready, /-/healthy |
| Grafana | Mini | 3001 | http://127.0.0.1:3001 | /api/health |
| OpenVINO LLM | Mini | 9000 | http://127.0.0.1:9000 | /health |
| Voice Gateway | Orin | 18080 | http://192.168.1.93:18080/v1 | /health, /health/readiness |
| OptiLLM proxy (Studio) | Studio | 4020 | http://192.168.1.72:4020/v1 | /v1/models |
| Studio main vector DB (postgres+pgvector) | Studio | 55432 | http://127.0.0.1:55432 | n/a |
| Studio main memory API | Studio | 55440 | http://127.0.0.1:55440 | /health |
| SearXNG | Mini | 8888 | http://127.0.0.1:8888 | not documented |
| MLX inference lane (active) | Studio | 8101 | http://192.168.1.72:8101/v1 | /v1/models |
| llmster GPT service (active for `fast` + `deep`) | Studio | 8126 | http://192.168.1.72:8126/v1 | /v1/models |
| AFM (planned) | Studio | 9999 | http://192.168.1.72:9999/v1 | /v1/models |
| Ollama | Mini | 11434 | http://192.168.1.71:11434 | not documented |
| Home Assistant | DietPi | 8123 | http://192.168.1.70:8123 | not documented |

### MLX port management
- Ports 8100-8119 are team slots on the Studio and managed via `platform/ops/scripts/mlxctl`.
- Ports 8120-8139 are reserved for experimental test loads; these ports do not require `mlxctl`.
- Current active public inference listeners:
  - `8101`: `vllm serve` under `com.bebop.mlx-lane.8101`
  - `8126`: `llmster` GPT service under `com.bebop.llmster-gpt.8126`
- Retired GPT rollback MLX slots:
  - `8100`
  - `8102`
- Approved additional owned labels for active service work:
  - `com.bebop.llmster-gpt.8126`
  - `com.bebop.optillm-proxy`

Studio scheduling contract:
- inference lane labels: `com.bebop.mlx-lane.8100`, `com.bebop.mlx-lane.8101`, `com.bebop.mlx-lane.8102`, `com.bebop.optillm-proxy`
- non-inference transient automation runs with taskpolicy utility clamp
- strict allowlist policy for owned labels (`com.bebop.*`, `com.deploy.*`)
- details: `docs/foundation/studio-scheduling-policy.md`

Note: on the Studio, `GET /v1/models` may return a local snapshot path as the model `id`.
Use `mlxctl status` as the canonical “which mlx-* model is on which port” signal for `8100-8119`.
This section governs the public/team-lane MLX control surface only. It does not
define the contract for specialized runtime-plane services such as
`omlx-runtime`.

### Orin speech appliance (status)
- `voice-gateway` is the approved LAN-visible speech facade on Orin.
- Speaches remains localhost-only behind `voice-gateway`.
- LiteLLM routes speech aliases directly to the Orin `voice-gateway` LAN `/v1` endpoint.
- Open WebUI must use LiteLLM for STT/TTS and must not call the Orin directly.
- Studio OptiLLM proxy serves LiteLLM `boost` and is unrelated to the speech appliance path.

## MCP Tools
- `web.fetch` — stdio MCP tool on the Mini (no network port).
- `search.web` — stdio MCP tool that calls LiteLLM `/v1/search`, backed by SearXNG.
- Open Terminal MCP — HTTP MCP backend on the Mini at `127.0.0.1:8011/mcp`,
  currently localhost-only. Open WebUI registers this backend directly as a
  read-only MCP tool server while preserving the native Open Terminal UI path
  on `127.0.0.1:8010`. A shared LiteLLM read-only alias is follow-on work and
  is not part of the current live runtime.

## Exposure and Secrets
- LAN-exposed: OpenVINO 9000 (maintenance), Voice Gateway 18080, Ollama 11434, Open WebUI 3000, OpenCode Web 4096, Samba SMB 139/445, Home Assistant 8123.
- LAN-first on Mini: LiteLLM 4000 on `192.168.1.71` (localhost remains valid).
- LAN-only from trusted local hosts: Studio MLX `8101` and Studio `llmster`
  `8126` via `192.168.1.72`.
- `8126` is the active shared `fast` + `deep` `llmster` GPT service.
- `8123-8125` are retired Studio shadow ports and are not part of the current
  control-plane target set.
- There are no active temporary GPT canary aliases in the current LiteLLM
  surface.
- Tailnet-only OpenCode Web operator path: `https://codeagent.tailfd1400.ts.net/` via `svc:codeagent`.
- Local-only: Prometheus 9090, Grafana 3001, SearXNG 8888, Open Terminal API
  8010, Open Terminal MCP 8011, CCProxy API 4010.
  OpenHands Phase A is systemd-managed on `127.0.0.1:4031` with tailnet-only
  operator access at `https://hands.tailfd1400.ts.net/` via `svc:hands`.
  Studio local-only: main vector DB 55432, memory API 55440.
- Internal tailnet transport used by Studio OptiLLM upstream:
  - `http://192.168.1.71:4000/v1`
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Env/secrets live outside the repo:
  - LiteLLM: `services/litellm-orch/config/env.local`
  - Open WebUI: `/etc/open-webui/env`
  - OpenCode Web: `/etc/opencode/env`
  - OpenVINO: `/etc/homelab-llm/ov-server.env`
  - SearXNG: `/etc/searxng/env`
  - Samba passdb: `smbpasswd -a christopherbailey` / `pdbedit`
  `/etc/openhands/env` carries non-secret runtime vars only; provider/API keys
  stay UI-entered in Phase A.

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

## Speech Contract
- LiteLLM is the only client-facing speech gateway.
- Open WebUI uses `AUDIO_STT_*` and `AUDIO_TTS_*` values pointed at LiteLLM.
- LiteLLM routes `voice-stt-canary`, `voice-tts-canary`, `voice-stt`, and `voice-tts`
  directly to the Orin `voice-gateway` LAN `/v1` facade.
- `voice-gateway` maps external voice aliases `default` and `alloy` to the configured
  Kokoro backend voice and forwards STT/TTS to localhost-only Speaches.
