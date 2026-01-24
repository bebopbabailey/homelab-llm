# 2026-01-19 — MLX default ensemble boot config

## Summary
Set the Studio boot ensemble to the three MLX models below and standardized
large defaults for context and output tokens.

## Boot ensemble (Studio)
- `mlx-gpt-oss-120b-mxfp4-q4` → port `8100`
- `mlx-qwen3-next-80b-a3b-instruct-mxfp4` → port `8101`
- `mlx-gpt-oss-20b-mxfp4-q4` → port `8102`

## Defaults
- `context_length`: **131072** (128k) for all three models.
- LiteLLM defaults after `mlxctl sync-gateway`:
  - `max_input_tokens: 131072`
  - `max_output_tokens: 65536`
  - `max_tokens: 65536`
Note: `max_output_tokens` will move into the upcoming `models` table (planned).

## Parsing
- GPT‑OSS models use Harmony parsers:
  - `--tool-call-parser harmony`
  - `--reasoning-parser harmony`
- Open WebUI displays clean output (no raw Harmony tags).

## Files
- Studio boot config: `/opt/mlx-launch/bin/start.sh`
- MLX registry: `/Users/thestudio/models/hf/hub/registry.json`
- Gateway routing: `layer-gateway/litellm-orch/config/router.yaml`
- Handles: `layer-gateway/registry/handles.jsonl`
