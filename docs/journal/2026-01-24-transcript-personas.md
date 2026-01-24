# 2026-01-24 — Transcript personas finalized

## Summary
- Implemented transcript presets as LiteLLM personas (pre-call hook).
- Presets strip punctuation outside words, preserve apostrophes in words, and apply a strict transcript-cleaning prompt.
- Added `p-transcript` (plain text) and `p-transcript-md` (Markdown allowed, minimal) alongside `char-transcript`.

## Decisions
- Transcript personas are **locked** and treated as production defaults.
- Default model for transcript personas: **medium** (`mlx-qwen3-next-80b-mxfp4-a3b-instruct`).
- Expressiveness: vivid (not dramatic), balanced pacing, rare exclamations.
- Word correction: moderate — only when intent is clearly implied.
- Output: cleaned transcript only; no metadata, summaries, or commentary.

## Behavior details
- Punctuation defaults to commas/periods; em-dashes/ellipses/semicolons allowed sparingly.
- Inner-voice quotes allowed when clearly implied ("I thought / I was like").

## Implementation
- `layer-gateway/litellm-orch/config/persona_router.py`
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/docs/personas.md`

## Tests
- Verified `p-transcript` and `p-transcript-md` responses against longer, varied transcripts.
- No truncation observed in tests.
