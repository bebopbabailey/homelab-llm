# Topology (Current)

This is the current runtime layout (Mini + Studio). Update when ports or bindings change.

## Mini (Ubuntu, always-on)
- **LiteLLM (gateway)**: `0.0.0.0:4000` (tailnet via Tailscale Serve)
- **Open WebUI**: `0.0.0.0:3000` (tailnet via Tailscale Serve)
- **Prometheus**: `127.0.0.1:9090` (localhost only)
- **Grafana**: `127.0.0.1:3001` (localhost only)
- **OpenVINO LLM**: `0.0.0.0:9000`
- **SearXNG**: `127.0.0.1:8888` (localhost only)
- **websearch-orch**: `127.0.0.1:8899` (localhost only)
- **Ollama**: `0.0.0.0:11434` (do not modify)

## Studio (macOS, MLX)
- **MLX launchd labels**: `com.bebop.mlx-lane.8100`, `com.bebop.mlx-lane.8101`, `com.bebop.mlx-lane.8102`
- **Active inference listeners**: `:8100/:8101/:8102` served by `vllm serve` under the matching per-lane labels
- Team ports: `8100–8119` (`mlxctl`-managed); experimental: `8120–8139` (no `mlxctl` requirement)
- **OptiLLM proxy**: `0.0.0.0:4020` (active LiteLLM `boost` path)

## Contracts
- Clients call **LiteLLM** only (`https://gateway.<tailnet>/v1` or localhost for on-host services).
- Open WebUI web search currently calls `websearch-orch` (`http://127.0.0.1:8899/search?q=<query>`) with external loader at `http://127.0.0.1:8899/web_loader`.
- LiteLLM also exposes `/v1/search/searxng-search` backed by SearXNG.
- MLX team ports (`8100–8119`) are managed via `platform/ops/scripts/mlxctl`.
- LiteLLM `boost` routes to Studio OptiLLM proxy on `192.168.1.72:4020`.
- Studio OptiLLM upstream currently reaches Mini LiteLLM via tailnet TCP forward `100.69.99.60:4443`.
- Studio scheduling is strict two-lane (inference vs utility); see `docs/foundation/studio-scheduling-policy.md`.
