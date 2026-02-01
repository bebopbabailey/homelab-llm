# 2026-01-24 — Transcript personas finalized

## Summary
- Deprecated: transcript personas were removed in favor of stable task handles.
- Current contract uses `task-transcribe` and `task-transcribe-vivid` with a minimal post-call cleaner.

## Decisions
- Transcript personas are **locked** and treated as production defaults.
- Default model for transcript personas: **large** (`mlx-gpt-oss-120b-mxfp4-q4`).
- Expressiveness: vivid (not theatrical), balanced pacing, rare exclamations.
- Word correction: none — wording is preserved; only disfluencies may be removed.
- Output: cleaned transcript only; no metadata, summaries, or commentary.

## Behavior details
- Punctuation defaults to commas/periods; em-dashes/ellipses/semicolons encouraged when they improve rhythm.
- Inner-voice quotes allowed when clearly implied ("I thought / I was like").

## Implementation
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/litellm-orch/config/transcribe_guardrail.py`

## Tests
- Verified `p-transcribe` responses against longer, varied transcripts.
- No truncation observed in tests.
