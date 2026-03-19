# Voice Gateway

Voice Gateway is the homelab's repo-owned speech boundary on the Orin.

Current canonical role:
- LAN-reachable OpenAI-compatible speech facade on the Orin
- forwards STT/TTS to localhost-only Speaches on the same host
- normalizes external model aliases (`whisper-1`, `tts-1`)
- normalizes external voice aliases (`default`, `alloy`)
- emits structured logs for speech requests and readiness checks
- exposes a CLI-first control plane (`voicectl`) backed by curated repo registry data

Non-goals for the canonical serving path:
- direct Open WebUI -> Orin speech calls
- direct LiteLLM -> Speaches calls
- diarization in the default Open WebUI voice-turn path

Control-plane source of truth:
- curated TTS registry: `registry/tts_models.jsonl`
- control-plane CLI: `voicectl`
- operator dashboard: `GET /ops`
- deploy provenance manifest: `.deploy-manifest.json` (path configurable)

Start here:
- `SERVICE_SPEC.md`
- `RUNBOOK.md`
- `ARCHITECTURE.md`
