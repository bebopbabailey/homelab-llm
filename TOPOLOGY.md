# Topology (Current)

This is the current runtime layout (Mini + Studio + Orin speech appliance). Update when ports or bindings change.

## Mini (Ubuntu, always-on)
- **LiteLLM (gateway)**: `0.0.0.0:4000` (canonical infra path `http://192.168.1.71:4000/v1`; localhost still valid)
- **Open WebUI**: `0.0.0.0:3000` (tailnet via Tailscale Serve)
- **OpenCode Web**: `0.0.0.0:4096` (Basic Auth; writable workspace limited to `~/homelab-llm`)
- **OpenHands (Phase A, operator-local)**: `127.0.0.1:4031` (manual Docker-direct session; optional tailnet-only access at `https://hands.tailfd1400.ts.net/`)
- **Samba SMB**: `127.0.0.1,192.168.1.71:139/445` (LAN-only; Finder shares `mini-root` and `seagate`)
- **Prometheus**: `127.0.0.1:9090` (localhost only)
- **Grafana**: `127.0.0.1:3001` (localhost only)
- **OpenVINO LLM**: `0.0.0.0:9000`
- **SearXNG**: `127.0.0.1:8888` (localhost only)
- **Ollama**: `0.0.0.0:11434` (do not modify)

## Studio (macOS, MLX)
- **MLX launchd labels**: `com.bebop.mlx-lane.8100`, `com.bebop.mlx-lane.8101`, `com.bebop.mlx-lane.8102`
- **Active inference listeners**: `192.168.1.72:8100/:8101/:8102` served by `vllm serve` under the matching per-lane labels
- Team ports: `8100–8119` (`mlxctl`-managed); experimental: `8120–8139` (no `mlxctl` requirement)
- **OptiLLM proxy**: `192.168.1.72:4020` (active LiteLLM `boost` path)
- **Main vector store (active, Studio-local)**:
  - Postgres+pgvector `127.0.0.1:55432` (`com.bebop.pgvector-main`)
  - Memory API `127.0.0.1:55440` (`com.bebop.memory-api-main`)
  - Internal retrieval backend mode: `MEMORY_BACKEND=legacy|haystack` (no port change)
  - Nightly ingest/backup jobs (`com.bebop.memory-ingest-nightly`, `com.bebop.memory-backup-nightly`)

## Orin (speech appliance)
- **Voice Gateway**: `192.168.1.93:18080` (LAN-visible OpenAI-compatible speech facade)
- **Speaches**: localhost-only behind `voice-gateway`

## Contracts
- Clients call **LiteLLM** only (`http://192.168.1.71:4000/v1` on LAN, `http://127.0.0.1:4000/v1` on Mini, tailnet optional for remote operator access).
- Open WebUI voice uses dedicated `AUDIO_STT_*` / `AUDIO_TTS_*` settings pointed at LiteLLM only.
- LiteLLM routes `voice-stt-canary`, `voice-tts-canary`, `voice-stt`, and `voice-tts`
  directly to the Orin `voice-gateway` LAN `/v1` facade.
- `voice-gateway` maps external voice aliases `default` and `alloy` to the configured
  Kokoro backend voice and forwards STT/TTS to localhost-only Speaches.
- OpenHands Phase A is a local bring-up exception for worker-mechanics validation only:
  Docker-direct on `127.0.0.1:4031`, optional tailnet-only access on
  `https://hands.tailfd1400.ts.net/`, disposable workspace mount only,
  temporary provider key entered in the UI, no LiteLLM wiring yet.
- OpenCode Web uses a hardened systemd sandbox. Approval prompts do not override
  filesystem policy; repo writes are allowed only inside `/home/christopherbailey/homelab-llm`
  plus OpenCode state/cache paths.
  Tailnet operator URL is `https://codeagent.tailfd1400.ts.net/` via dedicated
  Tailscale Service `svc:codeagent`.
- Finder SMB on the Mini is password-auth only for user `christopherbailey`.
  Direct LAN connection URLs are `smb://192.168.1.71/mini-root` and
  `smb://192.168.1.71/seagate`.
  `mini-root` maps to `/` but hides `/proc`, `/sys`, `/dev`, and `/run`.
- Open WebUI web search uses documented native config:
  `WEB_SEARCH_ENGINE=searxng`,
  `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`,
  `WEB_SEARCH_RESULT_COUNT=6`,
  `WEB_SEARCH_CONCURRENT_REQUESTS=1`,
  `WEB_LOADER_ENGINE=safe_web`,
  `WEB_LOADER_TIMEOUT=15`,
  `WEB_LOADER_CONCURRENT_REQUESTS=2`,
  `WEB_FETCH_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`,
  `WEB_SEARCH_DOMAIN_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`.
- LiteLLM also exposes `/v1/search/searxng-search` backed by SearXNG.
- MLX team ports (`8100–8119`) are managed via `platform/ops/scripts/mlxctl`.
- LiteLLM `main` / `deep` / `fast` route to Studio MLX lanes on `192.168.1.72:8100/8101/8102`.
- Studio OptiLLM upstream currently reaches Mini LiteLLM via the Mini LAN URL `http://192.168.1.71:4000/v1`.
- Studio scheduling is strict two-lane (inference vs utility); see `docs/foundation/studio-scheduling-policy.md`.
