# NOW — Preset Design + Testing

## Current focus
Design and test LiteLLM presets (`p-*`) for general use, with OptiLLM chaining and
clear behavior tiers (fast / safe / deep / chat + super variants). Finalize the
transcribe presets (`p-transcribe`, `p-transcribe-vivid`, `p-transcribe-clarify`) and confirm iOS
Shortcuts usage. Keep OpenCode config aligned with current handles and tool access.

## Scope
- Confirm preset naming and mapping (p-fast / p-safe / p-deep / p-chat, + super).
- Validate preset behavior via LiteLLM/OptiLLM (routing, chain applied, responses).
- Document SDLC mapping and usage guidance.
- Keep config + docs aligned with current reality.
- Transcribe presets: confirm vivid/neutral rules, large model default, and
  Shortcuts request body.

## Out of scope (for now)
- OptiLLM local inference (Studio)
- New model downloads/conversions
- New registries beyond presets/handles
