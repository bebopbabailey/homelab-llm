# Voice Gateway — SERVICE SPEC

## Status
- Canonical repo-owned speech boundary for the homelab.
- Canonical serving host: Orin (`192.168.1.93`).
- Backend engine: localhost-only Speaches on the same Orin.

## Purpose
Expose a stable OpenAI-compatible `/v1` speech surface for LiteLLM while hiding
backend-specific model IDs, voice IDs, and warm-model appliance policy.

## Exposure
- Service bind: loopback, `0.0.0.0`, or an explicit private LAN IP on the Orin.
- Approved canonical serving path: LiteLLM on the Mini routes directly to the
  Orin `voice-gateway` LAN address.
- Speaches remains localhost-only behind `voice-gateway`.

## Supported endpoints
- `GET /health`
- `GET /health/readiness`
- `GET /v1/models`
- `GET /v1/speakers`
- `POST /v1/audio/speech`
- `POST /v1/audio/transcriptions`

## Operator endpoints (MVP)
- `GET /ops` (embedded dashboard UI)
- `GET /ops/api/state`
- `GET /ops/api/registry/curated`
- `GET /ops/api/models/local`
- `GET /ops/api/models/registry`
- `GET /ops/api/models/loaded`
- `GET /ops/api/model-voices`
- `POST /ops/api/models/download`
- `POST /ops/api/models/load`
- `POST /ops/api/models/unload`
- `POST /ops/api/preview`
- `POST /ops/api/promotion/plan`

Operator endpoint policy:
- all `/ops/api/*` routes require the same bearer token policy as `/v1/*`
- model selection defaults to repo-curated entries from `registry/tts_models.jsonl`
- dashboard changes do not write root-owned config files directly
- production model/alias promotion remains manual via generated `sudo` command plans

## External model contract
- TTS: `tts-1`
- STT: `whisper-1`

These external model names are stable facade aliases. `voice-gateway` maps them
to concrete Speaches model IDs.

## External voice contract
- `default`
- `alloy`

Current policy:
- both aliases map to the same initial Kokoro backend voice
- config owns the concrete backend voice value
- unknown voices reject with HTTP 400 by default
- optional deterministic fallback is allowed only when config explicitly enables it

## Example `POST /v1/audio/speech`
```json
{
  "model": "tts-1",
  "input": "Hello from the homelab.",
  "voice": "alloy",
  "response_format": "mp3",
  "speed": 1.0
}
```

## Example `POST /v1/audio/transcriptions`
- multipart form with:
  - `file`
  - `model=whisper-1`
  - optional `language`
  - optional `prompt`
  - optional `response_format`
  - optional `temperature`
  - optional `timestamp_granularities[]`

Current native-STT wrapper response-format behavior:
- `response_format` unset, `json`, or `verbose_json` -> JSON `{ "text": "..." }`
- `response_format=text` -> `text/plain`
- `response_format=srt` or `response_format=vtt` -> HTTP `400` (`unsupported_response_format`)

## Warm appliance policy
Speaches must be configured with:
- `PRELOAD_MODELS` including the chosen canary STT model and Kokoro TTS model
- `STT_MODEL_TTL=-1` or an intentionally long appliance value
- `TTS_MODEL_TTL=-1` or an intentionally long appliance value

Initial recommendation:
- `STT_MODEL_TTL=-1`
- `TTS_MODEL_TTL=-1`

## Environment variables
Gateway service/runtime:
- `VOICE_GATEWAY_API_KEY` (optional bearer auth for `/v1/*` and `/ops/api/*`)
- `VOICE_CONFIG_PATH`
- `VOICE_LOG_PATH`
- `VOICE_LOG_LEVEL`
- `VOICE_BACKEND_API_BASE` (default `http://127.0.0.1:8000/v1`)
- `VOICE_BACKEND_API_KEY` (optional)
- `VOICE_BACKEND_TIMEOUT_SECONDS`
- `VOICE_PUBLIC_STT_MODEL` (default `whisper-1`)
- `VOICE_PUBLIC_TTS_MODEL` (default `tts-1`)
- `VOICE_BACKEND_STT_MODEL`
- `VOICE_BACKEND_TTS_MODEL`
- `VOICE_STT_BACKEND_API_BASE` (optional STT-only backend override)
- `VOICE_DEFAULT_LANGUAGE`

Control-plane/runtime metadata:
- `VOICE_TTS_REGISTRY_PATH` (default `<service-root>/registry/tts_models.jsonl`)
- `VOICE_DEPLOY_MANIFEST_PATH` (default `<service-root>/.deploy-manifest.json`)

Legacy local XTTS CLI settings (non-canonical for serving path):
- `VOICE_TTS_MODEL`
- `VOICE_TTS_DEVICE`

Service bind note:
- `voice-gateway-service` requires explicit `--host` and `--port` arguments.
- production bind values are owned by systemd `ExecStart`.

CLI defaults:
- `voicectl` supports `VOICE_GATEWAY_BASE_URL` and `VOICE_GATEWAY_API_KEY`.

## Config files
- voice alias config example: `config/voices.example.json`
- curated tts model registry: `registry/tts_models.jsonl`

## Control-plane CLI
- `voicectl` is the supported CLI entrypoint for curated TTS operations.
- initial supported commands:
  - `voicectl registry-list`
  - `voicectl status`
  - `voicectl download <curated-id-or-model-id>`
  - `voicectl load <curated-id-or-model-id>`
  - `voicectl unload <curated-id-or-model-id>`
  - `voicectl promotion-plan <curated-id-or-model-id> [--voice-ids ...]`

Deployment prerequisite:
- after adding/updating project entrypoints, run `uv sync --frozen` in the deploy checkout
  so `.venv/bin/voicectl` is installed before operator use.

## Observability fields
- `ts_utc`
- `event`
- `request_id`
- `route`
- `source`
- `model`
- `backend_model`
- `voice`
- `resolved_voice`
- `backend_voice`
- `input_chars` / `input_bytes`
- `output_bytes`
- `backend_upstream_ms`
- `total_ms`
- `status`
- `error_code`
- `exception_class`

## Diarization posture
- Diarization is required as a deliverable.
- It is not part of the default Open WebUI voice-turn path.
- Promotion of any diarization-capable enriched transcription format is blocked
  until end-to-end LiteLLM/OpenAI-compatible transcription testing proves the
  chosen response shape does not break clients.
