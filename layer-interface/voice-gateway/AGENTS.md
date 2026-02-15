# Agent Guidance: Voice Gateway

## Scope
Only change `layer-interface/voice-gateway/*`.

## Non-negotiables
- Voice Gateway must call LiteLLM only (`http://127.0.0.1:4000/v1` on-host).
- Do not call MLX/OpenVINO/OptiLLM directly.
- Do not expose LAN listeners without an explicit plan and approval.
- Do not commit secrets (API keys, tokens, device identifiers that are sensitive).

## Before edits
- Re-read `layer-interface/CONSTRAINTS.md` and `layer-interface/DEPENDENCIES.md`.

