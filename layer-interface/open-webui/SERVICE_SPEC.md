# Service Spec: Open WebUI

## Purpose
Human-facing UI for LLM and voice interactions routed through LiteLLM.

## Interface
- HTTP UI: `0.0.0.0:3000`
- Health: `GET /health`

## Dependencies
- LiteLLM proxy at `http://127.0.0.1:4000/v1`
- Speech path:
  - Open WebUI -> LiteLLM only
  - LiteLLM -> Orin `voice-gateway` only
  - Open WebUI must not call the Orin directly for STT or TTS
- Local SearXNG JSON endpoint via documented Open WebUI config

## Configuration
- `/etc/open-webui/env` (systemd `EnvironmentFile`)
- `/etc/systemd/system/open-webui.service.d/*.conf` (service overrides)
- data stored in `/home/christopherbailey/.open-webui`

## Audio configuration surface
- `AUDIO_STT_ENGINE`
- `AUDIO_STT_OPENAI_API_BASE_URL`
- `AUDIO_STT_OPENAI_API_KEY`
- `AUDIO_STT_MODEL`
- `AUDIO_TTS_ENGINE`
- `AUDIO_TTS_OPENAI_API_BASE_URL`
- `AUDIO_TTS_OPENAI_API_KEY`
- `AUDIO_TTS_MODEL`
- `AUDIO_TTS_VOICE`
- `AUDIO_TTS_OPENAI_PARAMS`
- `AUDIO_TTS_SPLIT_ON`

## Canonical canary values
- `AUDIO_STT_ENGINE=openai`
- `AUDIO_STT_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`
- `AUDIO_STT_MODEL=voice-stt-canary`
- `AUDIO_TTS_ENGINE=openai`
- `AUDIO_TTS_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`
- `AUDIO_TTS_MODEL=voice-tts-canary`
- `AUDIO_TTS_VOICE=alloy`

## Config authority
- `ENABLE_PERSISTENT_CONFIG=False` is required for this path.
- systemd env/drop-ins are authoritative across restart.
- canary promotion requires post-restart verification that no stale Admin UI audio
  state is overriding the expected env-driven values.

## Ownership boundary
- Open WebUI owns the human UI and audio UX.
- LiteLLM remains the single client-facing gateway for LLM, STT, and TTS.
- `voice-gateway` remains the repo-owned speech boundary on the Orin.
