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
- **MLX Omni LaunchDaemon**: `com.bebop.mlx-omni.8100` (canonical endpoint `:8100`; team ports `8100–8119`; experimental `8120–8139`)
- **Legacy disabled**: `com.bebop.mlx-launch` (per-port `mlx-openai-server`)
- **OptiLLM proxy**: `0.0.0.0:4020` (active LiteLLM `boost` path)

## Contracts
- Clients call **LiteLLM** only (`https://gateway.<tailnet>/v1` or localhost for on-host services).
- Tool search flows through LiteLLM `/v1/search` to SearXNG.
- MLX ports are managed via `platform/ops/scripts/mlxctl`.
- LiteLLM `boost` routes to Studio OptiLLM proxy on `192.168.1.72:4020`.
