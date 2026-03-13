# Voice Gateway — SERVICE SPEC

## Status
- This document defines the Phase 1 implementation contract for Voice Gateway.
- It does not assert that Voice Gateway is already deployed on the Orin.

## Phase 1 Scope
Voice Gateway Phase 1 is a **TTS-only interface service** for the Orin:
- XTTS-v2 text-to-speech generation
- local CLI/debug path
- localhost-only HTTP wrapper
- WAV-only output

Phase 1 does **not** include:
- STT
- LiteLLM runtime calls
- cloned voice enrollment
- LAN reachability
- public exposure

## Classification
- Layer: Interface
- Type: Local audio utility + localhost wrapper
- Exposure: localhost-only in Phase 1

## Host Placement (Phase 1)
- Host: Orin (`192.168.1.93`)
- Reason: Orin is the local audio box and the intended host for later voice work.

## Current Gate
- XTTS runtime/bootstrap proof is closed in the repo-tracked proof container.
- XTTS model materialization and first one-shot synth are closed on the Orin.
- B6 localhost wrapper proof is closed:
  - thin wrapper-proof image built from the proven runtime image
  - container-local bind `0.0.0.0`
  - Docker publish `127.0.0.1:18080:18080`
  - no host networking
  - `GET /health` and `GET /health/readiness` succeeded
  - `GET /v1/speakers` succeeded
  - one localhost `POST /v1/audio/speech` succeeded
  - one DAC playback smoke using the returned WAV succeeded
- The next consumer is Open WebUI TTS on the Mini through a Mini-local SSH forward to the Orin loopback wrapper.
- The next phase is no longer XTTS bootstrap recovery.

## Dependencies
### Required
- Local audio output device (speaker / default sink)
- Repo-tracked runtime build inputs
- Real environment proof on the Orin before any more feature work

### Built-in Voice Discovery
- Phase 1 discovers built-in XTTS speakers at runtime.
- No built-in speaker name is hardcoded in code, docs, or config examples.
- The default voice resolves by policy (`first_discovered_builtin`) unless an
  alias maps to a discovered built-in speaker.

### Deferred
- STT backend
- LiteLLM integration
- clone/reference-WAV enrollment
- Home Assistant integration

## Interfaces

### CLI (primary acceptance path)
- `voice-gateway list-speakers`
- `voice-gateway synth --text ... --voice ... --out ... [--play]`

### HTTP Wrapper (localhost only)
- `GET /health`
- `GET /health/readiness`
- `GET /v1/speakers`
- `POST /v1/audio/speech`

### `POST /v1/audio/speech` Request
```json
{
  "model": "xtts-v2",
  "input": "Hello from the Orin.",
  "voice": "default",
  "response_format": "wav",
  "language": "en"
}
```

### `POST /v1/audio/speech` Rules
- `model` must be `xtts-v2`
- `response_format` must be `wav`
- `voice` resolves through built-in discovery/config policy
- `voice` defaults to `default`
- `response_format` defaults to `wav`
- `language` defaults to `en`
- response body is `audio/wav`

### Deferred HTTP Features
- STT endpoints
- streaming audio
- uploaded `speaker_wav`
- playback side effects
- LiteLLM/gateway fields

## Environment Variables

- `VOICE_GATEWAY_HOST` (default: `127.0.0.1`; B6 wrapper proof uses container-local `0.0.0.0` with loopback-only host publish)
- `VOICE_GATEWAY_PORT` (required only for serve mode; no default port is assigned here)
- `VOICE_CONFIG_PATH` (default: `/etc/voice-gateway/voices.json`)
- `VOICE_LOG_PATH` (optional JSONL file sink)
- `VOICE_LOG_LEVEL` (`INFO` | `DEBUG`)
- `VOICE_TTS_MODEL` (default: `tts_models/multilingual/multi-dataset/xtts_v2`)
- `VOICE_TTS_DEVICE` (`auto` | `cpu` | `cuda`)
- `VOICE_DEFAULT_LANGUAGE` (default: `en`)

## Runtime Recovery Contract
Closed runtime/bootstrap proof includes:
- successful repo-tracked container build on Orin
- successful imports for `torch`, `torchaudio`, maintained `coqui-tts`, and `soundfile`
- successful `torch.cuda.is_available()` call without crash
- successful XTTS model materialization under `/srv/ssd/models/voice-gateway`
- successful first one-shot WAV under `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`

Closed B6 proof does **not** include:
- STT
- non-local clients
- LAN/public exposure
- service-owned playback side effects

## Current Consumer Direction
- Current next consumer: Open WebUI TTS running on the Mini.
- Current minimum reachability path:
  - Mini loopback `127.0.0.1:18081`
  - SSH forward target `orin:127.0.0.1:18080`
- No direct LAN bind is approved for this service.

## Data Produced
- WAV output files from CLI synthesis
- structured JSON log events
- discovered built-in speaker inventory

## Observability Fields
- `ts_utc`
- `request_id`
- `source`
- `route`
- `model`
- `speaker_id`
- `resolved_builtin_speaker`
- `language`
- `input_chars`
- `speaker_discovery_ms`
- `model_load_ms`
- `synth_ms`
- `wav_write_ms`
- `playback_ms`
- `total_ms`
- `output_bytes`
- `status`
- `error_code`
- `exception_class`

## Failure Handling Rules
- Never hang silently.
- On synth failure:
  - return a deterministic CLI/API error
  - log details and timings
- Playback failures must not corrupt synthesized WAV output.

## Deferred To Later Phases
- STT
- LiteLLM orchestration
- cloned voices
- reference WAV enrollment
- direct non-local clients beyond the controlled Mini-local SSH forward path
- LAN exposure

## Non-Goals (Phase 1)
- Wake word
- remote mic
- full voice loop
- public or LAN exposure
