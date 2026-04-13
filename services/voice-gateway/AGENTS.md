# Agent Guidance: Voice Gateway

## Scope
Only change `services/voice-gateway/*`.

## Non-negotiables
- LiteLLM is the required path for future LLM calls from Voice Gateway
  (LiteLLM runs on the Mini; set via env, do not hardcode).
- Local STT/TTS engines inside the Voice Gateway service boundary are allowed.
- Do not call MLX/OpenVINO/OptiLLM directly.
- Do not expose LAN listeners without an explicit plan and approval.
- Do not commit secrets (API keys, tokens, device identifiers that are sensitive).

## Before edits
- Re-read `layer-interface/CONSTRAINTS.md` and `layer-interface/DEPENDENCIES.md`.
- Treat `services/voice-gateway/*` as the canonical service root during the migration.
