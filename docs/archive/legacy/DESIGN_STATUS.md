# Design Status (Working Notes)

Date: 2026-01-24

## Current design focus
Presets are the active design axis for the system. We are standardizing how
LiteLLM exposes stable aliases (`main`, `deep`, `fast`, `swap`), how OptiLLM chaining is applied, and how
clients (Open WebUI, OpenCode, Shortcuts) consume these presets.

## Active decisions
- Presets live in LiteLLM (gateway) as aliases that bundle base model, system prompt,
  default params, and OptiLLM approach.
- Preset tiers: fast / safe / deep / chat, with optional “super” variants for extra compute.
- Keep client usage minimal: callers only choose a preset name.
- Transcribe tasks are finalized in LiteLLM (`task-transcribe`, `task-transcribe-vivid`) with
  server-side punctuation stripping and vivid-but-not-theatrical rules.
- Transcript personas default to the medium MLX model (`mlx-qwen3-next-80b-mxfp4-a3b-instruct`).

## Open questions (current)
- Whether to formalize a presets registry file + validator.
- How to expose per-approach compute knobs (BoN N, MoA agent count) in presets.
