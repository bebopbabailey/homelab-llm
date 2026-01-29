# NOW — Preset Design + Testing

## Current focus
Design and test LiteLLM aliases (`main`, `deep`, `fast`, `swap`) for general use, with OptiLLM chaining and
clear behavior tiers (core + experimental). Finalize the
transcribe tasks (`task-transcribe`, `task-transcribe-vivid`) and confirm iOS
Shortcuts usage. Keep OpenCode config aligned with current handles and tool access.

## Scope
- Confirm alias naming and mapping (main / deep / fast / swap, + x1..x4).
- Validate preset behavior via LiteLLM/OptiLLM (routing, chain applied, responses).
- Document SDLC mapping and usage guidance.
- Keep config + docs aligned with current reality.
- Transcribe tasks: confirm vivid/neutral rules, large model default, and
  Shortcuts request body.

## Out of scope (for now)
- OptiLLM local inference (Studio)
- New model downloads/conversions
- New registries beyond presets/handles
