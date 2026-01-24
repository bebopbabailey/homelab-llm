# NOW — Preset Design + Testing

## Current focus
Design and test LiteLLM presets (`p-*`) for general use, with OptiLLM chaining and
clear behavior tiers (fast / safe / deep / chat + super variants). Finalize the
transcript-cleaning presets (`p-transcript`, `p-transcript-md`) and confirm iOS
Shortcuts usage.

## Scope
- Confirm preset naming and mapping (p-fast / p-safe / p-deep / p-chat, + super).
- Validate preset behavior via LiteLLM/OptiLLM (routing, chain applied, responses).
- Document SDLC mapping and usage guidance.
- Keep config + docs aligned with current reality.
- Transcript presets: confirm vivid/neutral rules, medium model default, and
  Shortcuts request body.

## Out of scope (for now)
- OptiLLM local inference (Studio)
- New model downloads/conversions
- New registries beyond presets/handles
