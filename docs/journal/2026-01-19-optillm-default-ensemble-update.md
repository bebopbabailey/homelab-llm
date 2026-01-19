# 2026-01-19 — OptiLLM default ensemble refresh

- Default MLX boot ensemble is now two models:
  - `mlx-gpt-oss-120b-mlx-mxfp4`
  - `mlx-llama-3-1-70b-instruct-4bit`
- OptiLLM proxy handles are now router-only:
  - `opt-router-gpt-oss-120b-mlx-mxfp4`
  - `opt-router-llama-3-1-70b-instruct-4bit`
- Removed multi-technique OptiLLM proxy handles in the gateway configs to keep
  routing logic inside OptiLLM.
- Documentation and LiteLLM env/router configs updated to match.
