# PLATFORM_DOSSIER

## Topology (current)
- Mac Mini: LiteLLM :4000 (LAN + localhost; tailnet optional for remote operator access), Open WebUI :3000 (LAN + tailnet),
  OpenCode Web :4096 (LAN + tailnet-reachable if network policy allows, Basic Auth at app layer),
  OpenHands Phase A :4031 (localhost + tailnet via `hands`, systemd-managed Docker service),
  Samba SMB :139/:445 (LAN-only authenticated Finder access to `mini-root` and `seagate`),
  Prometheus :9090 (localhost-only), Grafana :3001 (localhost-only),
  OpenVINO :9000 (LAN-exposed for maintenance),
  SearXNG :8888 (localhost-only), Ollama :11434
- Mac Studio: MLX inference host using the `mlxctl`-governed team-lane domain
  (`8100-8119`, with active public MLX lane `192.168.1.72:8101`).
  Retired GPT rollback slots `8100` and `8102` remain in the `mlxctl` domain
  but are unloaded.
  Public LLM canon is `deep`, `main`, and `fast`, with `main` on Qwen3-Next at `8101`
  and `fast` plus `deep` on shared `llmster` at `8126`.
  OptiLLM proxy :4020 remains deployed but is not part of the active gateway alias surface.
  Studio main vector-store services (localhost-only): Postgres+pgvector `:55432`,
  memory API `:55440`, nightly ingest/backup jobs.
- Jetson Orin AGX: canonical speech appliance host.
  `voice-gateway` is the approved LAN-visible speech facade and fronts localhost-only
  Speaches for STT/TTS. Current host identity and runtime status are canonical in
  `docs/foundation/orin-agx.md`.
- HP DietPi: Home Assistant :8123
## Topology (planned)
- Mac Studio: AFM (Apple Foundation Models) OpenAI-compatible API (target: :9999), routed via LiteLLM.

## Ports and endpoints (authoritative)

| service | host | port | bind | base URL | health | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| LiteLLM proxy | Mini | 4000 | 0.0.0.0 | http://192.168.1.71:4000 | /health, /health/readiness, /health/liveliness | `/etc/systemd/system/litellm-orch.service`, `systemctl show litellm-orch.service -p ExecStart`, `ss -ltnp` |
| Open WebUI | Mini | 3000 | 0.0.0.0 | http://192.168.1.71:3000 | /health | `/etc/systemd/system/open-webui.service`, `systemctl show open-webui.service -p ExecStart`, `ss -ltnp` |
| OpenCode Web | Mini | 4096 | 0.0.0.0 | http://127.0.0.1:4096 | UI root (401 unauthenticated) | `/etc/systemd/system/opencode-web.service`, `systemctl show opencode-web.service -p ExecStart`, `ss -ltnp` |
| OpenHands (Phase A, managed operator UI) | Mini | 4031 | 127.0.0.1 | http://127.0.0.1:4031, https://hands.tailfd1400.ts.net/ | UI root | `/etc/systemd/system/openhands.service`, `systemctl show openhands.service -p ExecStart`, `ss -ltnp`, `tailscale serve status --json` |
| Samba SMB | Mini | 139/445 | `127.0.0.1` + `192.168.1.71` | smb://192.168.1.71/mini-root, smb://192.168.1.71/seagate | `testparm -s`, Finder auth | `/etc/samba/smb.conf`, `systemctl status smbd.service nmbd.service`, `pdbedit -L` |
| Prometheus | Mini | 9090 | 127.0.0.1 | http://127.0.0.1:9090 | /-/ready, /-/healthy | `/usr/lib/systemd/system/prometheus.service`, `/etc/default/prometheus` |
| Grafana | Mini | 3001 | 127.0.0.1 | http://127.0.0.1:3001 | /api/health | `/usr/lib/systemd/system/grafana-server.service`, `/etc/default/grafana-server` |
| OpenVINO LLM | Mini | 9000 | 0.0.0.0 | http://127.0.0.1:9000 | /health | `/etc/systemd/system/ov-server.service`, `/etc/homelab-llm/ov-server.env` |
| Voice Gateway | Orin | 18080 | private LAN IP | http://192.168.1.93:18080/v1 | /health, /health/readiness | `layer-interface/voice-gateway/SERVICE_SPEC.md`, Orin service/container runtime |
| OptiLLM proxy | Studio | 4020 | 192.168.1.72 | http://192.168.1.72:4020/v1 | /v1/models | `layer-gateway/optillm-proxy`, deployed but not part of the active LiteLLM alias surface |
| Studio main vector DB | Studio | 55432 | 127.0.0.1 | http://127.0.0.1:55432 | n/a | `com.bebop.pgvector-main`, policy-managed launchd |
| Studio main memory API | Studio | 55440 | 127.0.0.1 | http://127.0.0.1:55440 | /health | `com.bebop.memory-api-main`, policy-managed launchd |
| SearXNG | Mini | 8888 | 127.0.0.1 | http://127.0.0.1:8888 | not documented | `/etc/systemd/system/searxng.service`, `/etc/searxng/settings.yml` |
| MLX inference lane (active) | Studio | 8101 | 192.168.1.72 | http://192.168.1.72:8101/v1 | /v1/models | `com.bebop.mlx-lane.8101`, runtime `vllm serve`, `mlxctl status` |
| llmster GPT service (active for `fast` + `deep`) | Studio | 8126 | 192.168.1.72 | http://192.168.1.72:8126/v1 | /v1/models | `com.bebop.llmster-gpt.8126`, runtime `llmster`, `lms ps --json` |
| AFM (planned) | Studio | 9999 | 0.0.0.0 | http://192.168.1.72:9999/v1 | /v1/models | owner confirmation (not yet wired) |
| Ollama | Mini | 11434 | 0.0.0.0 | http://192.168.1.71:11434 | not documented | `/etc/systemd/system/ollama.service`, `/etc/systemd/system/ollama.service.d/override.conf` |
| Home Assistant | DietPi | 8123 | 0.0.0.0 (assumed) | http://192.168.1.70:8123 | not documented | `/home/christopherbailey/.ssh/config`, owner confirmation |

Networking note:
- The canonical Mini -> Studio MLX transport is the Studio LAN IP `192.168.1.72`.
- Tailscale hostnames are not part of the active MLX lane transport contract.

### Port immutability
- Do not change or reuse ports without an explicit port-migration phase.

## Service inventory (concise)
- LiteLLM: systemd unit `/etc/systemd/system/litellm-orch.service`, json logs in `layer-gateway/litellm-orch/config/router.yaml`.
  Auth: API calls require `Authorization: Bearer <LITELLM_MASTER_KEY>` (even on localhost).
  Health/auth behavior: `/v1/*` and `/health` are auth-gated; `/health/readiness`,
  `/health/liveliness`, and `/metrics/` are currently open.
  Runtime lock baseline: `drop_params=true`, `fast -> main`.
  Current package baseline: `litellm[proxy]==1.83.4`.
  Additional task aliases: `task-transcribe` and `task-transcribe-vivid` route
  to the current `8101` Qwen lane for transcript cleanup through
  `POST /v1/chat/completions`; they are not speech STT endpoints.
  Utility alias: `task-json` routes to the current `fast` backend through
  `POST /v1/chat/completions` and returns canonical transcript-to-JSON output.
  Mini-side Prisma/schema repair was required on the current LiteLLM 1.83.4
  deployment before `/key/generate` and `/v1/mcp/*` worked again. The
  repo-managed systemd unit now must keep
  `ENFORCE_PRISMA_MIGRATION_CHECK=true` so drift fails fast on startup.
  ChatGPT device auth can complete on Mini through LiteLLM's provider flow, but
  stable `1.83.4` still fails real `chatgpt/...` inference after auth, so no
  ChatGPT-backed alias is part of the accepted public gateway contract.
  Utility alias: `task-json` routes to the current `fast` backend through
  `POST /v1/chat/completions` and returns canonical transcript-to-JSON output.
  Prometheus metrics: `/metrics/` (same port; use trailing slash).
  GPT formatting/tool-call parsing is upstream-owned for `main`, `fast`, and
  `deep`; LiteLLM retains only a narrow request-default shim for omitted
  `reasoning_effort` on `fast`/`deep`.
  GPT lanes remain Chat Completions-first in the current hardening phase;
  `/v1/responses` stays advisory unless a defect there also matters to the
  public Chat Completions path.
  Temporary rollout-only gateway aliases are permitted during GPT cutovers when
  they do not redefine the public alias surface; current approved example:
  no active temporary GPT rollout aliases.
  GPT lanes now preserve caller streaming intent by default (no forced `stream=false`).
- Prometheus: systemd unit `/usr/lib/systemd/system/prometheus.service`, config `/etc/homelab-llm/prometheus/prometheus.yml`.
- Grafana: systemd unit `/usr/lib/systemd/system/grafana-server.service`, config `/etc/homelab-llm/grafana/grafana.ini`,
  provisioning `/etc/homelab-llm/grafana/provisioning/`.
- Open WebUI: systemd unit `/etc/systemd/system/open-webui.service`, env `/etc/open-webui/env`, data `/home/christopherbailey/.open-webui`.
  Working dir: `/home/christopherbailey/homelab-llm/layer-interface/open-webui` (legacy `/home/christopherbailey/open-webui` may exist).
  Canonical speech path uses env-driven `AUDIO_STT_*` / `AUDIO_TTS_*` values pointed at LiteLLM speech aliases only.
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
  Speech canary promotion requires a post-restart check that no stale Admin UI audio state overrides the env-backed audio settings.
- Open Terminal:
  - native human-UX API container remains on `127.0.0.1:8010`
  - canonical shared MCP backend is `open-terminal-mcp.service` on `127.0.0.1:8011/mcp`
  - runtime is Docker under systemd from a derived image pinned to upstream `open-terminal`
  - first slice mount scope is repo-root only:
    `/home/christopherbailey/homelab-llm:/lab/homelab-llm:ro`
  - terminal/notebook features are disabled for the MCP lane
  - shared LiteLLM exposure is still blocked on current stable runtime
  - OpenHands remains denied for `/v1/mcp/*`
- OpenCode Web: systemd unit `/etc/systemd/system/opencode-web.service`, env `/etc/opencode/env`.
  Repo-managed source of truth: `platform/ops/systemd/opencode-web.service`.
  Runtime bind is `0.0.0.0:4096` with HTTP Basic Auth.
  Hardening stays enabled (`ProtectSystem=strict`, `ProtectHome=read-only`).
  Writable allowlist is limited to OpenCode state/cache dirs plus `/home/christopherbailey/homelab-llm`.
  OpenCode approval prompts do not override the systemd sandbox.
- OpenHands (Phase A): repo-managed `systemd` + Docker service on `127.0.0.1:4031`.
  Tailnet operator path is `https://hands.tailfd1400.ts.net/`
  backed by `tailscale serve --service=svc:hands`.
  Host runtime files are `/etc/systemd/system/openhands.service` and `/etc/openhands/env`.
  Primary launch contract is the repo-managed unit `platform/ops/systemd/openhands.service`.
  Docker sandbox only; mount only a disposable workspace into `/workspace`.
  Temporary provider/API key is entered in the UI only and is not wired through repo
  config or LiteLLM in this phase. `/etc/openhands/env` is limited to non-secret
  runtime vars only.
  LiteLLM Phase B uses one reserved/internal worker alias only:
  `code-reasoning -> deep`.
  The governed Phase B contract is:
  `litellm_proxy/code-reasoning` + OpenHands service-account key only.
  Canonical container path is `http://host.docker.internal:4000/v1`.
  `http://192.168.1.71:4000/v1` remains the verified fallback/reference path.
  MCP and `/v1/responses` remain denied for the worker key.
  If the custom host persistence mount is not honored during first smoke,
  fall back to the exact documented `~/.openhands:/.openhands` mount and clean it
  up after the session.
- Samba SMB: package-managed `smbd.service` + `nmbd.service` on the Mini.
  Canonical live config is `/etc/samba/smb.conf`; repo template is
  `platform/ops/templates/samba-mini-shares.conf`.
  Current Finder contract is password-auth SMB for user `christopherbailey`,
  LAN-only on `127.0.0.1` + `192.168.1.71`, with shares:
  `mini-root` -> `/` and `seagate` -> `/mnt/seagate`.
  `mini-root` hides pseudo-filesystems `/proc`, `/sys`, `/dev`, and `/run`
  and uses `hide unreadable = yes`.
- OpenVINO: systemd unit `/etc/systemd/system/ov-server.service`, env `/etc/homelab-llm/ov-server.env`.
  OpenVINO is currently available as a standalone backend and is not wired as active LiteLLM handles.
  int4 on GPU is unstable (kernel compile failure); CPU-only int4 is possible but lower fidelity.
  Current env: `OV_DEVICE=GPU`, `OV_MODEL_PATH` fallback is fp32 (historical; registry is used for OpenVINO).
  Next evaluation: `OV_DEVICE=AUTO` and `OV_DEVICE=MULTI:GPU,CPU` for multi-request throughput.
- Voice Gateway: repo-owned speech facade on the Orin. LiteLLM routes `voice-stt-canary`,
  `voice-tts-canary`, `voice-stt`, and `voice-tts` directly to the Orin LAN `/v1`
  facade. `voice-gateway` maps external voice aliases (`default`, `alloy`) to the
  configured Kokoro backend voice and forwards STT/TTS to localhost-only Speaches.
  Operator control plane is CLI-first (`voicectl`) with dashboard support at `/ops`.
  Canonical TTS candidate set is repo-curated in
  `layer-interface/voice-gateway/registry/tts_models.jsonl`; live Speaches registry is discovery-only.
  Live deployment evidence is tracked in `docs/foundation/orin-agx.md` and
  includes deploy provenance surfaced from `/ops/api/state` when
  `.deploy-manifest.json` is present in the deploy checkout.
  Speaches appliance policy preloads the chosen canary STT and Kokoro TTS models and
  keeps `STT_MODEL_TTL` / `TTS_MODEL_TTL` at `-1` or another intentionally long value.
- OptiLLM proxy (Studio): managed by launchd.
  Evidence: `/Library/LaunchDaemons/com.bebop.optillm-proxy.plist`.
  Runtime args include: `--host 192.168.1.72 --port 4020 --model main --base-url http://192.168.1.71:4000/v1`.
  Upstream: Mini LiteLLM via the Mini LAN URL `http://192.168.1.71:4000/v1`.
  LiteLLM routes `boost` to this proxy via `OPTILLM_API_BASE`.
  Deploy contract is exact-SHA from repo checkout with `uv sync --frozen`.
  Current package baseline is `optillm==0.3.12` from PyPI with no deploy-time patching.
  Historical trio canary work used the local `plansearchtrio` plugin.
- SearXNG: systemd unit `/etc/systemd/system/searxng.service`, env `/etc/searxng/env`, localhost-only.
- MLX: ports 8100-8119 are team slots managed via `platform/ops/scripts/mlxctl`; 8120-8139 are experimental test ports and do not require `mlxctl`.
  Current active public MLX inference listener: `8101` (`vllm serve` under
  `com.bebop.mlx-lane.8101`).
  Retired GPT rollback MLX slots: `8100` and `8102` are unloaded.
  Active non-MLX inference labels:
  `com.bebop.llmster-gpt.8126` and `com.bebop.optillm-proxy`.
  Retired shadow labels:
  `com.bebop.mlx-shadow.8123`, `com.bebop.mlx-shadow.8124`,
  `com.bebop.mlx-shadow.8125`.
- MLX registry (`/Users/thestudio/models/hf/hub/registry.json`) maps canonical `model_id`
  to `source_path`/`cache_path` for inference.
  Registry version 2 also carries explicit per-lane state:
  `desired_target`, `actual_serving_target`, `last_known_good_target`,
  `health_state`, `reconciliation_state`, and `last_failure`.
  Only models present on Mini/Studio are exposed as LiteLLM handles (Seagate is backroom).
  Current team-lane runtime command family is `vllm serve` (`vllm-metal`) under per-lane launchd labels.
  Runtime lock baseline: `VLLM_METAL_MEMORY_FRACTION=auto`, no backend bearer auth, `--no-async-scheduling`, paged attention off.
  `mlxctl` now compiles per-lane vLLM args from registry (including strict parser
  capability validation for auto-tool lanes) plus required family metadata from
  `platform/ops/mlx-runtime-profiles.json`. Current staged default enables
  auto-tool for `main` (`8101`) only, and the locked live `8101` render uses
  `--tool-call-parser hermes` with no `--reasoning-parser`.
  GPT-OSS family entries also carry logical chat-template kwargs; `mlxctl`
  compiles those into the `vllm-metal` argv via
  `--default-chat-template-kwargs` when the runtime supports it.
  Load success now requires explicit readiness:
  stable process, `/v1/models` identity match, and a successful minimal
  non-streaming `/v1/chat/completions` probe on two consecutive passes with no
  restart between them.
  Scheduling policy contract (strict two-lane + fail-closed allowlist):
  `docs/foundation/studio-scheduling-policy.md`.
- llmster GPT service boundary: canonical public path is LiteLLM on Mini ->
  `llmster` on Studio -> llama.cpp runtime. Raw standalone `llama-server`
  mirrors remain loopback-only diagnostic seams and are not the public path.
  Shared `8126` is the accepted working posture for public `fast` and `deep`,
  with explicit residency proof and post-load idle memory evidence captured
  before the `deep` cutover.
- Ollama: systemd unit `/etc/systemd/system/ollama.service`.
- Home Assistant: OS package on DietPi, systemd-managed, root-run (owner confirmation).
- MCP tools:
  - stdio: `web.fetch`, `search.web`
  - HTTP backend on Mini: Open Terminal MCP at `127.0.0.1:8011/mcp`
    (localhost-only direct backend; shared LiteLLM exposure is not yet accepted
    runtime truth on the current stable build)
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
- LAN-exposed: OpenVINO 9000 (maintenance), Voice Gateway 18080, Ollama 11434, Open WebUI 3000, OpenCode Web 4096, Samba SMB 139/445, Home Assistant 8123.
- LAN-first on Mini: LiteLLM 4000 on `192.168.1.71` with localhost still valid.
- LAN-only from trusted local hosts: Studio MLX `8101` and Studio `llmster`
  `8126` on `192.168.1.72`.
- Local-only: Prometheus 9090, Grafana 3001, SearXNG 8888, Open Terminal API
  8010, Open Terminal MCP 8011.
- Local-only bind with tailnet-only operator access: OpenHands Phase A 4031 at `https://hands.tailfd1400.ts.net/`.
- Local-only (Studio): main vector DB 55432, memory API 55440.
- Tailnet HTTPS (Tailscale Serve on Mini):
  - `https://code.tailfd1400.ts.net/` → code-server (8080)
  - `https://chat.tailfd1400.ts.net/` → Open WebUI (3000)
  - `https://codeagent.tailfd1400.ts.net/` → OpenCode Web (4096)
  - `https://gateway.tailfd1400.ts.net/` → LiteLLM (4000)
  - `https://hands.tailfd1400.ts.net/` → OpenHands (4031)
  - `https://search.tailfd1400.ts.net/` → SearXNG (8888)
- Tailnet remains optional/operator-only and is not part of the canonical Mini ↔ Studio service path.
- Retired shadow ports `8123-8125` are not part of the current live exposure
  set.
- OpenVINO binds 0.0.0.0 for maintenance; internal callers use localhost.
- Secrets/envs: `config/env.local`, `/etc/open-webui/env`, `/etc/homelab-llm/ov-server.env`, `/etc/searxng/env`, Samba passdb via `smbpasswd` / `pdbedit`.
  OpenHands Phase A uses `/etc/openhands/env` for non-secret runtime vars only.
  OpenHands Phase B should not reuse a human LiteLLM key; it uses a team
  service-account key stored outside git.
- Tailscale ACLs/grants managed in admin (use `svc:*` grants for Services access).

## Decisions (ADR-lite)
- LiteLLM is the single gateway.
- Plain logical model names for clients.
- Ports treated as immutable.
- Approved four-lane rollout keeps public aliases stable while backend families
  vary behind LiteLLM: MAIN remains on MLX-family backends, FAST/DEEP move
  through `llmster`/llama.cpp.
