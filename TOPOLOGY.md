# Topology (Current)

This is the current runtime layout (Mini + Studio + Orin speech appliance). Update when ports or bindings change.

## Mini (Ubuntu, always-on)
- **LiteLLM (gateway)**: `0.0.0.0:4000` (canonical infra path `http://192.168.1.71:4000/v1`; localhost still valid)
- **Open WebUI**: `0.0.0.0:3000` (tailnet via Tailscale Serve)
- **orchestration-cockpit prototype (inactive by default)**:
  LangGraph dev `127.0.0.1:2024`, Agent Chat UI `127.0.0.1:3030`
- **CCProxy API (experimental)**: `127.0.0.1:4010` (`/codex/v1`, localhost-only Codex sidecar behind LiteLLM)
- **Open Terminal API**: `127.0.0.1:8010` (optional native Open WebUI human UX path)
- **Open Terminal MCP**: `127.0.0.1:8011` (`/mcp`, localhost-only direct backend; shared LiteLLM alias is future work)
- **OpenCode Web**: `0.0.0.0:4096` (Basic Auth; writable workspace limited to `~/homelab-llm`)
- **OpenHands (Phase A, managed operator UI)**: `127.0.0.1:4031` (systemd-managed Docker service; tailnet-only access at `https://hands.tailfd1400.ts.net/`)
- **Samba SMB**: `127.0.0.1,192.168.1.71:139/445` (LAN-only; Finder shares `mini-root` and `seagate`)
- **Prometheus**: `127.0.0.1:9090` (localhost only)
- **Grafana**: `127.0.0.1:3001` (localhost only)
- **OpenVINO LLM**: `0.0.0.0:9000`
- **SearXNG**: `127.0.0.1:8888` (localhost only)
- **Ollama**: `0.0.0.0:11434` (do not modify)

## Studio (macOS, MLX)
- **MLX launchd labels**: `com.bebop.mlx-lane.8100`, `com.bebop.mlx-lane.8101`, `com.bebop.mlx-lane.8102`
- **Active MLX public inference listener**: `192.168.1.72:8101` served by `vllm serve` under `com.bebop.mlx-lane.8101`
- **Retired GPT rollback MLX slots**: `8100` and `8102` are still `mlxctl`-governed team ports, but they are now unloaded and are not part of the active public stack
- Team ports: `8100–8119` (`mlxctl`-managed); experimental: `8120–8139` (no `mlxctl` requirement)
- **Active non-MLX inference labels**:
  `com.bebop.llmster-gpt.8126`, `com.bebop.optillm-proxy`
- **Active non-MLX listeners**:
  `192.168.1.72:4020/:8126`
  with `8126` live for shared `fast` + `deep`; `4020` remains non-core
  operator infrastructure
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
- Direct backend URLs in this document are operator-only validation or
  service-to-service paths, not approved client entrypoints.
- Open WebUI voice uses dedicated `AUDIO_STT_*` / `AUDIO_TTS_*` settings pointed at LiteLLM only.
- LiteLLM routes `voice-stt-canary`, `voice-tts-canary`, `voice-stt`, and `voice-tts`
  directly to the Orin `voice-gateway` LAN `/v1` facade.
- `voice-gateway` maps external voice aliases `default` and `alloy` to the configured
  Kokoro backend voice and forwards STT/TTS to localhost-only Speaches.
- Voice control plane is repo-first:
  - curated registry: `layer-interface/voice-gateway/registry/tts_models.jsonl`
  - operator CLI: `voicectl`
  - operator dashboard/API: `/ops` and `/ops/api/*`
- OpenHands Phase A is a managed bring-up exception for worker-mechanics validation only:
  systemd-managed Docker on `127.0.0.1:4031`, tailnet-only access on
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
- Open Terminal MCP currently remains a localhost-only direct backend at
  `127.0.0.1:8011/mcp`; a shared LiteLLM MCP alias is follow-on work and is
  not part of the current live runtime.
- Open WebUI may keep the native Open Terminal API path on `127.0.0.1:8010`
  for human UX; it remains intentionally separate from the MCP backend.
- MLX team ports (`8100–8119`) are managed via `platform/ops/scripts/mlxctl`.
- LiteLLM `main` routes to the Studio MLX lane on `192.168.1.72:8101`.
- LiteLLM `fast` and `deep` route to Studio `llmster` on `192.168.1.72:8126`.
- `orchestration-cockpit` is a local orchestration prototype only and does not
  replace LiteLLM, Open WebUI, or the commodity gateway contract.
- There are no active temporary GPT rollout aliases in the public LiteLLM
  surface.
- GPT lanes are currently Chat Completions-first; `/v1/responses` remains
  available for direct callers where supported.
- `chatgpt-5` now routes through the Mini-local `ccproxy-api` sidecar on
  `127.0.0.1:4010/codex/v1`.
- Shadow rollout listeners `8123-8125` are retired and are not part of the
  active gateway alias surface.
- Studio OptiLLM upstream currently reaches Mini LiteLLM via the Mini LAN URL `http://192.168.1.71:4000/v1`.
- Studio scheduling is strict two-lane (inference vs utility); see `docs/foundation/studio-scheduling-policy.md`.
