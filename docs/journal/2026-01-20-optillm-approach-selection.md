# 2026-01-20 — OptiLLM approach selection via request body

**Status:** Updated. OptiLLM is called directly; LiteLLM no longer routes through it.

- Switched OptiLLM technique selection to per-request `optillm_approach` (no model-name prefixes).
- The older router-mlx loop-avoidance wiring is deprecated.
- LiteLLM still keeps `litellm_settings.drop_params: false` for pass-through when needed.
