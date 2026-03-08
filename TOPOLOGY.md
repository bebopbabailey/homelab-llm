# Topology (Current)

This is the current runtime layout (Mini + Studio). Update when ports or bindings change.

## Mini (Ubuntu, always-on)
- **LiteLLM (gateway)**: `0.0.0.0:4000` (tailnet via Tailscale Serve)
- **Open WebUI**: `0.0.0.0:3000` (tailnet via Tailscale Serve)
- **Prometheus**: `127.0.0.1:9090` (localhost only)
- **Grafana**: `127.0.0.1:3001` (localhost only)
- **OpenVINO LLM**: `0.0.0.0:9000`
- **SearXNG**: `127.0.0.1:8888` (localhost only)
- **Ollama**: `0.0.0.0:11434` (do not modify)

## Studio (macOS, MLX)
- **MLX launchd labels**: `com.bebop.mlx-lane.8100`, `com.bebop.mlx-lane.8101`, `com.bebop.mlx-lane.8102`
- **Active inference listeners**: `:8100/:8101/:8102` served by `vllm serve` under the matching per-lane labels
- Team ports: `8100–8119` (`mlxctl`-managed); experimental: `8120–8139` (no `mlxctl` requirement)
- **OptiLLM proxy**: `0.0.0.0:4020` (active LiteLLM `boost` path)
- **Main vector store (active, Studio-local)**:
  - Postgres+pgvector `127.0.0.1:55432` (`com.bebop.pgvector-main`)
  - Memory API `127.0.0.1:55440` (`com.bebop.memory-api-main`)
  - Internal retrieval backend mode: `MEMORY_BACKEND=legacy|haystack` (no port change)
  - Nightly ingest/backup jobs (`com.bebop.memory-ingest-nightly`, `com.bebop.memory-backup-nightly`)

## Contracts
- Clients call **LiteLLM** only (`https://gateway.<tailnet>/v1` or localhost for on-host services).
- Open WebUI web search uses documented native config:
  `WEB_SEARCH_ENGINE=searxng`,
  `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`,
  `WEB_SEARCH_RESULT_COUNT=6`,
  `WEB_SEARCH_CONCURRENT_REQUESTS=1`,
  `WEB_LOADER_ENGINE=safe_web`,
  `WEB_LOADER_TIMEOUT=15`,
  `WEB_LOADER_CONCURRENT_REQUESTS=2`,
  `WEB_FETCH_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`,
  `WEB_SEARCH_DOMAIN_FILTER_LIST=["!localhost","!127.0.0.1","!192.168.1.70","!192.168.1.71","!192.168.1.72","!100.69.99.60","!code.tailfd1400.ts.net","!chat.tailfd1400.ts.net","!gateway.tailfd1400.ts.net","!search.tailfd1400.ts.net"]`.
- LiteLLM also exposes `/v1/search/searxng-search` backed by SearXNG.
- MLX team ports (`8100–8119`) are managed via `platform/ops/scripts/mlxctl`.
- LiteLLM `boost` routes to Studio OptiLLM proxy on `192.168.1.72:4020`.
- Studio OptiLLM upstream currently reaches Mini LiteLLM via tailnet TCP forward `100.69.99.60:4443`.
- Studio scheduling is strict two-lane (inference vs utility); see `docs/foundation/studio-scheduling-policy.md`.
