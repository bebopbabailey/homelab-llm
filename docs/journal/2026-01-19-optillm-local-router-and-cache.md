# 2026-01-19 — OptiLLM local router + HF cache standard

## Summary
- Standardized Studio HF cache path to `/Users/thestudio/models/hf/hub`.
- Cleaned duplicate HF downloads under `/Users/thestudio/models/hf/*` (moved or removed).
- OptiLLM local router now works after pinning `transformers<5`.
- MOA on local inference hit NaN during final decode at higher token counts; tabled for later tuning.
- Local test throughput on Qwen2.5-32B (router=none) ~7–9 tok/s after warm.
- LiteLLM GUI needs DB + master key to be re-enabled.
- OptiLLM local launchd is disabled until local inference setup is finalized.
- Default OptiLLM proxy handles now use router-only selectors:
  - `opt-router-gpt-oss-120b-mlx-mxfp4`
  - `opt-router-llama-3-1-70b-instruct-4bit`
- Standardized OptiLLM selectors to use `mlx-gpt-oss-120b-mlx-mxfp4` (matches MLX handle).

## Details
- Downloads restarted with HF token and ordered small → large.
- `optillm-local` balanced instance now pointed to Qwen2.5-32B for early testing.
- Router model loads via `codelion/optillm-modernbert-large`.
- Next: finish 57B/72B downloads, re-point high/balanced, revisit MOA stability.
