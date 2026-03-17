# Voice Gateway

Voice Gateway is the homelab's repo-owned speech boundary on the Orin.

Current canonical role:
- LAN-reachable OpenAI-compatible speech facade on the Orin
- forwards STT/TTS to localhost-only Speaches on the same host
- normalizes external model aliases (`whisper-1`, `tts-1`)
- normalizes external voice aliases (`default`, `alloy`)
- emits structured logs for speech requests and readiness checks

Non-goals for the canonical serving path:
- direct Open WebUI -> Orin speech calls
- direct LiteLLM -> Speaches calls
- XTTS serving concerns
- diarization in the default Open WebUI voice-turn path

Start here:
- `SERVICE_SPEC.md`
- `RUNBOOK.md`
- `ARCHITECTURE.md`
