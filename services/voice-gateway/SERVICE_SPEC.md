# Voice Gateway — SERVICE SPEC

## Status
- Canonical repo-owned speech boundary for the homelab.
- Canonical serving host: Orin (`192.168.1.93`).
- Backend engines: localhost-only native STT wrapper for transcription and
  localhost-only Speaches for TTS on the same Orin.

## Purpose
Expose a stable OpenAI-compatible `/v1` speech surface for LiteLLM while hiding
backend-specific model IDs, voice IDs, and warm-model appliance policy.

## Exposure
- Service bind: explicit private LAN IP on the Orin for the approved serving
  path.
- Approved canonical serving path: LiteLLM on the Mini routes directly to the
  Orin `voice-gateway` LAN address.
- Native STT and Speaches remain localhost-only behind `voice-gateway`.

## Supported endpoints
- `GET /health`
- `GET /health/readiness`
- `GET /health/stt`
- `GET /v1/models`
- `GET /v1/speakers`
- `POST /v1/audio/speech`
- `POST /v1/audio/transcriptions`

## Operator endpoints
- `GET /ops`
- `GET /ops/api/state`
- `GET /ops/api/registry/curated`
- `POST /ops/api/promotion/plan`

## External model contract
- TTS: `tts-1`
- STT: `whisper-1`

## External voice contract
- `default`
- `alloy`

## Environment variables
- `VOICE_GATEWAY_API_KEY`
- `VOICE_CONFIG_PATH`
- `VOICE_BACKEND_API_BASE`
- `VOICE_STT_BACKEND_API_BASE`
- `VOICE_BACKEND_STT_MODEL`
- `VOICE_BACKEND_TTS_MODEL`
- `VOICE_TTS_REGISTRY_PATH`

Service bind note:
- `voice-gateway-service` requires explicit `--host` and `--port` arguments.
- Production bind values are owned by systemd `ExecStart` and must stay aligned
  with the canonical LAN-serving contract.

Native STT note:
- The lightweight Orin transcription path uses `VOICE_STT_BACKEND_API_BASE`
  pointed at `http://127.0.0.1:18081` and default backend model `small.en`.
- `GET /health/stt` is allowed to report ready when transcription is ready even
  if whole-gateway readiness is blocked by TTS/Speaches.
