# Voice Gateway — SERVICE SPEC

## Role
Voice Gateway is a **local-only interface service** that provides the v1 voice loop:

Mic audio → STT → LiteLLM → TTS → speaker output

It is a **client of LiteLLM** (gateway) and must never call inference backends directly.

## Classification
- Layer: Interface
- Type: Client/orchestrator (no inference)
- Exposure: Localhost-only (no LAN exposure in v1)

## Host Placement (v1)
- Host: Mac Mini (Ubuntu)
- Reason: always-on, connected microphone (Shure MV51), co-located with LiteLLM gateway

## Dependencies
### Required
- LiteLLM (OpenAI-compatible)
  - Base URL (on-host): `http://127.0.0.1:4000/v1`
  - Auth: bearer token required (do not commit; comes from local deployment env)
- Local audio input device (USB mic)
- Local audio output device (speaker / default sink)

### Optional (v1.5+)
- Home Assistant endpoint (not used in v1)

## Interfaces

### Primary Interface (v1)
Command-line / systemd service:
- Push-to-talk activation
- Logs latency and failures
- Speaks results aloud

### Optional Local Control Interface (v1)
If an HTTP control plane is used, it MUST bind to localhost only:
- Bind: `127.0.0.1`
- Endpoints:
  - `GET /health`
  - `POST /ptt` (trigger one listen→respond cycle)
  - `POST /speak` (speak provided text, for diagnostics)

No LAN exposure without an explicit topology change and approval.

## Environment Variables

### Core
- `LITELLM_BASE_URL` (default: `http://127.0.0.1:4000/v1`)
- `LITELLM_MODEL` (logical model name, e.g. `mlx-qwen2-5-coder-32b-instruct-8bit` or `ov-qwen2-5-3b-instruct-fp16`)
- `SYSTEM_PROMPT` (short stable assistant prompt)
- `PTT_MODE` (`keyboard` | `gpio` | `none`) — v1 typically `keyboard`

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
