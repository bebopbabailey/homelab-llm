# Constraints: youtube-transcript-api

This service inherits global constraints from `../../CONSTRAINTS.md`.

## Hard constraints
- Bind localhost-only on the Mini.
- Implement YouTube transcript acquisition only.
- Preserve source caption language; no translation fallback.
- Do not call an LLM, summarize, clean, index, or store transcript content.
- Do not add direct LAN exposure or auth bypass behavior.

## Validation pointers
- `uv run pytest`
- `curl -fsS http://127.0.0.1:8014/health`
- LiteLLM chat completion through `model=task-youtube-transcript`
