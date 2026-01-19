# Topology (Current)

This is the current runtime layout (Mini + Studio). Update when ports or bindings change.

## Mini (Ubuntu, always-on)
- **LiteLLM (gateway)**: `0.0.0.0:4000`
- **Open WebUI**: `0.0.0.0:3000`
- **OpenVINO LLM**: `0.0.0.0:9000`
- **OptiLLM proxy**: `127.0.0.1:4020` (localhost only)
- **SearXNG**: `127.0.0.1:8888` (localhost only)
- **Ollama**: `0.0.0.0:11434` (do not modify)

## Studio (macOS, MLX)
- **MLX LaunchDaemon**: `com.bebop.mlx-launch` (ports `8100–8109` reserved)

## Contracts
- Clients call **LiteLLM** only (`http://<mini>:4000/v1`).
- Tool search flows through LiteLLM `/v1/search` to SearXNG.
- MLX ports are managed via `platform/ops/scripts/mlxctl`.
