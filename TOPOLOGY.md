# Topology (Current)

This is the current runtime layout (Mini + Studio). Update when ports or bindings change.

## Mini (Ubuntu, always-on)
- **LiteLLM (gateway)**: `127.0.0.1:4000` (tailnet via Tailscale Serve)
- **Open WebUI**: `127.0.0.1:3000` (tailnet via Tailscale Serve)
- **Prometheus**: `127.0.0.1:9090` (localhost only)
- **Grafana**: `127.0.0.1:3001` (localhost only)
- **OpenVINO LLM**: `0.0.0.0:9000`
- **SearXNG**: `127.0.0.1:8888` (localhost only)
- **Ollama**: `0.0.0.0:11434` (do not modify)

## Studio (macOS, MLX)
- **MLX per-port lanes** (`mlx_lm.server`):
  - `8100` deep (`mlx-gpt-oss-120b-mxfp4-q4`)
  - `8101` main (`mlx-qwen3-next-80b-mxfp4-a3b-instruct`)
  - `8102` fast (`mlx-gpt-oss-20b-mxfp4-q4`)
- Team ports: `8100–8119`; experimental: `8120–8139`
- **OptiLLM proxy**: `0.0.0.0:4020` (active LiteLLM `boost` path)

## Contracts
- Clients call **LiteLLM** only (`https://gateway.<tailnet>/v1` or localhost for on-host services).
- Tool search flows through LiteLLM `/v1/search` to SearXNG.
- MLX ports are managed via `platform/ops/scripts/mlxctl`.
- LiteLLM `boost` routes to Studio OptiLLM proxy on `192.168.1.72:4020`.
- Studio OptiLLM upstream currently reaches Mini LiteLLM via tailnet TCP forward `100.69.99.60:4443`.
