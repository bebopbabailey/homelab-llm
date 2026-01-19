# 2026-01-19 — MLX context defaults (all models)

## Summary
- Set LiteLLM defaults for **all MLX models** using each model’s local `config.json` on the Studio.
- Applied the same context-aware limits to all `opt-*` handles based on their base MLX model.

## Details
- `max_input_tokens` now comes from the MLX registry field `context_length`.
- `max_output_tokens` and `max_tokens` default to **65k** (unless overridden per model).
- This keeps defaults large while still honoring the model’s real context window.

## Files updated
- `layer-gateway/litellm-orch/config/router.yaml`
- `docs/foundation/mlx-registry.md`
- `docs/INTEGRATIONS.md`
