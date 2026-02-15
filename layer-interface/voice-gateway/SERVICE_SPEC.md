# Voice Gateway — SERVICE SPEC

## Role
Voice Gateway is an **internal interface service** that provides the v1 voice loop:

Mic audio → STT → LiteLLM → TTS → speaker output

It is a **client of LiteLLM** (gateway) and must never call inference backends directly.

## Classification
- Layer: Interface
- Type: Client/orchestrator (no inference)
- Exposure: LAN-private on the Orin. It must be reachable from the Mini
  (LiteLLM/Open WebUI) but must not be exposed to the public internet.

## Host Placement (v1)
- Host: Orin (`192.168.1.93`)
- Reason: Orin is the realtime audio box (STT/TTS). LiteLLM remains on the Mini.

## Dependencies
### Required
- LiteLLM (OpenAI-compatible)
  - Base URL: LiteLLM on the Mini (must be set via env; do not hardcode localhost)
  - Auth: bearer token required (do not commit; comes from local deployment env)
- Local audio input device (USB mic)
- Local audio output device (speaker / default sink)

### Optional (v1.5+)
- Home Assistant endpoint (not used in v1)

## Interfaces

### Primary Interface (v1)
HTTP API (internal) + systemd service on the Orin:
- STT endpoint (audio -> text)
- TTS endpoint (text -> audio)
- Optional "one-shot" voice loop endpoint (PTT / automation)

Implementation detail: we prefer OpenAI-compatible shapes where feasible
(e.g., `/v1/audio/transcriptions`, `/v1/audio/speech`), but the exact contract is
finalized during implementation.

### Local Admin / Control Interface (optional)
If a separate admin/control plane is introduced, it MUST bind to localhost only
on the Orin (e.g., for debugging, device selection, or diagnostics).

## Environment Variables

### Core
- `LITELLM_BASE_URL` (required; LiteLLM on the Mini, e.g. `http://<mini-ip>:4000/v1`)
- `LITELLM_MODEL` (logical model name, e.g. `mlx-qwen2-5-coder-32b-instruct-8bit` or `ov-qwen2-5-3b-instruct-fp16`)
- `SYSTEM_PROMPT` (short stable assistant prompt)
- `PTT_MODE` (`keyboard` | `gpio` | `none`) — v1 typically `keyboard`

### Service Networking (v1)
- `VOICE_GATEWAY_BIND_ADDR` (recommended: Orin LAN addr; do not bind to public interfaces)
- `VOICE_GATEWAY_PORT`

### Audio Device Selection
- `AUDIO_INPUT_DEVICE` (ALSA/Pulse device identifier; optional)
- `AUDIO_OUTPUT_DEVICE` (optional)

### STT
- `STT_BACKEND` (`whispercpp` | `fasterwhisper` | `openvino`) — start with one
- `STT_MODEL_PATH` (local model path)
- `STT_LANGUAGE` (e.g. `en`)

### TTS
- `TTS_BACKEND` (`piper` | `coqui` | `system`) — start with one
- `TTS_VOICE` (voice identifier)
- `TTS_RATE` (optional)

### Logging / Metrics
- `VOICE_LOG_PATH` (default: `/var/log/voice-gateway/voice.jsonl`)
- `VOICE_LOG_LEVEL` (`INFO` | `DEBUG`)

## Data Produced (Artifacts)
- JSONL per request:
  - timestamp
  - stt_ms
  - llm_ms
  - tts_ms
  - total_ms
  - selected_model
  - error_code (if any)

## Failure Handling Rules (v1)
- Never hang silently.
- On any stage failure:
  - speak a short failure message (“STT failed”, “LLM unavailable”, etc.)
  - log details and timings
- Timeouts:
  - STT timeout: 10s
  - LLM timeout: 15s
  - TTS timeout: 10s
- Retries:
  - at most 1 retry for the LiteLLM call (not STT/TTS)

## Non-Goals (v1)
- Wake word
- Remote mic
- Memory/RAG
- Tools/agents (beyond basic system prompts)
- Direct backend calls (prohibited)
