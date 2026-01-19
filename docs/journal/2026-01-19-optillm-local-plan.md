# 2026-01-19 — OptiLLM local inference plan (Studio)

## Summary
- Approved a separate local OptiLLM service on the Studio for decoding-time techniques.
- Selected three instances (high/balanced/fast) with clear handle names.

## Ports + handles (v0)
- `4040` → `opt-router-high`
- `4041` → `opt-router-balanced`
- `4042` → `opt-router-fast`

## Notes
- Local inference uses PyTorch/Transformers on MPS (Metal).
- Each instance serves a single model.
