# 2026-01-24 — Presets + SDLC mapping

## Context
- Presets are LiteLLM-side aliases that bundle model selection, system prompt, default params, and OptiLLM approach chaining.
- Goal: simplify client usage (Open WebUI, OpenCode, Shortcuts) while keeping consistent behavior.

## Decisions
- Keep presets centralized in LiteLLM; UI clients consume preset aliases.
- Introduce a minimal preset set for daily use:
  - `p-fast` (re2&bon)
  - `p-safe` (leap&re2&bon)
  - `p-deep` (leap&re2&bon&moa)
  - `p-chat` (leap&re2)
- Add “super” variants to spend more compute (future: per-approach knobs to differentiate).
- Map presets to SDLC stages for consistent usage:
  - Discovery/Requirements → `p-chat`
  - Architecture/Design → `p-deep` (or `p-deep-super`)
  - Planning/Estimation → `p-safe`
  - Implementation → `p-fast` (default) / `p-deep` (complex)
  - Testing/QA → `p-safe`
  - Debugging/Triage → `p-safe` or `char-duck`
  - Release/Docs → `p-chat` or `p-safe`
  - Maintenance/Refactor → `p-deep`

## Notes
- Presets improve consistency via fixed prompts, params, and chains but do not guarantee determinism.
- A future “preset registry” can formalize this and enable validation/CLI tooling.
