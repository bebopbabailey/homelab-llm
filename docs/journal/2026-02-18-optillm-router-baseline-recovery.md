# 2026-02-18 — OptiLLM router baseline recovery (encode_plus mismatch)

## Context
- `boost` / `boost-deep` requests were returning `200`, but OptiLLM router was not
  actually performing intelligent routing.
- Studio log evidence repeatedly showed:
  - `Error in router plugin: TokenizersBackend has no attribute encode_plus.`
  - `Falling back to direct model usage.`

## Root cause
- OptiLLM `router_plugin.py` calls `tokenizer.encode_plus(...)`.
- Studio runtime had:
  - `optillm==0.3.12`
  - `transformers==5.0.0`
  - `tokenizers==0.22.2`
- With this stack, `AutoTokenizer.from_pretrained("codelion/optillm-modernbert-large")`
  returned `TokenizersBackend` without `encode_plus`, causing router failure on every request.

## Decision
- Keep single OptiLLM instance on Studio `:4020`.
- Restore router compatibility by pinning a known-good tokenizer stack in
  `layer-gateway/optillm-proxy`:
  - `transformers==4.49.0`
  - `tokenizers==0.21.0`
- Do not patch OptiLLM router code in site-packages for this fix.

## Validation targets
- No new router fallback lines after service restart.
- Presence of `Router predicted approach: ...` in OptiLLM logs.
- `boost` and `boost-deep` remain successful through LiteLLM.

