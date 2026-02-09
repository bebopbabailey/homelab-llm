# Topology (Current)

This is the current runtime layout (Mini + Studio). Update when ports or bindings change.

## Mini (Ubuntu, always-on)
- **LiteLLM (gateway)**: `127.0.0.1:4000` (tailnet via Tailscale Serve)
- **Open WebUI**: `127.0.0.1:3000` (tailnet via Tailscale Serve)
- **Prometheus**: `127.0.0.1:9090` (localhost only)
- **Grafana**: `127.0.0.1:3001` (localhost only)
- **OpenVINO LLM**: `0.0.0.0:9000`
- **OptiLLM proxy**: `127.0.0.1:4020` (localhost only)
- **SearXNG**: `127.0.0.1:8888` (localhost only)
- **Ollama**: `0.0.0.0:11434` (do not modify)

## Studio (macOS, MLX)
- **MLX LaunchDaemon**: `com.bebop.mlx-launch` (team ports `8100–8119`; experimental `8120–8139`)

## Contracts
- Clients call **LiteLLM** only (`https://gateway.<tailnet>/v1` or localhost for on-host services).
- Tool search flows through LiteLLM `/v1/search` to SearXNG.
- MLX ports are managed via `platform/ops/scripts/mlxctl`.

- Orin: OptiLLM local on port 4040 (LAN only, routed via LiteLLM)
