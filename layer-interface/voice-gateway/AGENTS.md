# Agent Guidance: Voice Gateway

## Scope
Only change `layer-interface/voice-gateway/*`.

## Non-negotiables
- Voice Gateway must call LiteLLM only (LiteLLM runs on the Mini; set via env, do not hardcode).
- Do not call MLX/OpenVINO/OptiLLM directly.
- Do not expose LAN listeners without an explicit plan and approval.
- Do not commit secrets (API keys, tokens, device identifiers that are sensitive).

## Before edits
- Re-read `layer-interface/CONSTRAINTS.md` and `layer-interface/DEPENDENCIES.md`.
