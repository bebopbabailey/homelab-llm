# 2026-01-16 — Benny deprecation + ov-* alias alignment

## Summary
- Deprecated role-based `benny-*` aliases across LiteLLM/OpenVINO.
- Replaced with `ov-*` aliases that map directly to base OpenVINO model IDs.
- Archived legacy Benny prompts and onboarding docs under `docs/deprecated/`.

## Current ov-* aliases
- `ov-qwen2-5-3b-instruct-fp16`
- `ov-qwen2-5-1-5b-instruct-fp16`
- `ov-phi-4-mini-instruct-fp16`
- `ov-phi-3-5-mini-instruct-fp16`
- `ov-llama-3-2-3b-instruct-fp16`
- `ov-mistral-7b-instruct-v0-3-fp16`

## Notes
- OpenVINO warm profiles updated to `ov-only-{expanded,safe,fast}`.
- Future registry/DB should track quantization + model metadata (not alias names).
