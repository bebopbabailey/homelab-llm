# Voice Gateway — RUNBOOK

## Purpose
Operate the canonical Orin speech appliance facade used by LiteLLM.

## Appliance shape
- `voice-gateway` is the only approved LAN-visible speech listener on Orin.
- Speaches stays localhost-only behind it.
- LiteLLM on the Mini talks directly to `voice-gateway` over the Orin LAN address.

## Required backend policy
Configure Speaches with warm resident models:

```dotenv
PRELOAD_MODELS=["Systran/faster-distil-whisper-large-v3","speaches-ai/Kokoro-82M-v1.0-ONNX"]
STT_MODEL_TTL=-1
TTS_MODEL_TTL=-1
```

Use a finite TTL only if appliance memory pressure proves `-1` is unsafe.

## Ops dashboard (MVP)
The gateway serves an operator UI at `GET /ops` and API-backed actions under
`/ops/api/*`.

Repo-canonical model source:
- curated shortlist: `registry/tts_models.jsonl`
- remote Speaches registry remains discovery-only

- Model discovery:
  - curated registry: `GET /ops/api/registry/curated`
  - local models: `GET /ops/api/models/local?task=text-to-speech`
  - registry models: `GET /ops/api/models/registry?task=text-to-speech`
  - loaded models: `GET /ops/api/models/loaded`
- Model lifecycle:
  - download: `POST /ops/api/models/download`
  - load: `POST /ops/api/models/load`
  - unload: `POST /ops/api/models/unload`
- Audition:
  - `POST /ops/api/preview` (direct model + voice preview)

### Manual promotion policy
`/ops` generates shell plans via `POST /ops/api/promotion/plan` but does not
write root-owned runtime files automatically.

Promotion plan command bundle currently updates:
- `/etc/voice-gateway/voice-gateway.env` (`VOICE_BACKEND_TTS_MODEL`)
- `/etc/voice-gateway/voices.json`
- `voice-gateway.service` restart and readiness checks

## CLI-first control plane
Use `voicectl` for boring, scripted operations against the curated registry and
live gateway APIs.

Install/upgrade prerequisite in the deploy checkout:
```bash
cd /home/christopherbailey/voice-gateway-canary
uv sync --frozen
```

This ensures `.venv/bin/voicectl` is present after entrypoint changes.

Examples:
```bash
voicectl registry-list
voicectl --base-url http://192.168.1.93:18080 --api-key "$VOICE_GATEWAY_API_KEY" status
voicectl --base-url http://192.168.1.93:18080 --api-key "$VOICE_GATEWAY_API_KEY" download kokoro-fp16
voicectl --base-url http://192.168.1.93:18080 --api-key "$VOICE_GATEWAY_API_KEY" load kokoro-fp16
voicectl --base-url http://192.168.1.93:18080 --api-key "$VOICE_GATEWAY_API_KEY" promotion-plan kokoro-fp16 --voice-ids af_heart,af_nova
```

Environment defaults:
- `VOICE_TTS_REGISTRY_PATH` (curated JSONL path)
- `VOICE_DEPLOY_MANIFEST_PATH` (read-only deploy provenance manifest)

## Deploy provenance manifest
`/ops/api/state` exposes `deploy_manifest` when the configured manifest exists.

Recommended file:
- `/home/christopherbailey/voice-gateway-canary/.deploy-manifest.json`

Recommended fields:
- `repo_commit_sha`
- `service_path`
- `deployed_checkout`
- `deployed_at_utc`
- `deployed_by`

Apply model/voice promotions manually with `sudo` using generated commands:
- `/etc/voice-gateway/voice-gateway.env`
- `/etc/voice-gateway/voices.json`
- `sudo systemctl restart voice-gateway.service`

## Native STT wrapper (localhost-only, Orin)
The first-pass native STT wrapper runs as an internal localhost service and keeps
the proven host-native runtime pinned:

- `ctranslate2==4.7.1` (source-built CUDA-capable lane)
- `faster-whisper==1.1.1`
- model `Systran/faster-distil-whisper-large-v3`
- `device=cuda`, `compute_type=float16`
- `LD_LIBRARY_PATH` includes `/home/christopherbailey/stt-native-lab/ct2-prefix/lib`

Required env file (`/etc/voice-gateway/native-stt.env`):

```dotenv
NATIVE_STT_HOST=127.0.0.1
NATIVE_STT_PORT=18081
NATIVE_STT_MODEL=Systran/faster-distil-whisper-large-v3
NATIVE_STT_DEVICE=cuda
NATIVE_STT_COMPUTE_TYPE=float16
NATIVE_STT_CT2_VERSION=4.7.1
NATIVE_STT_FW_VERSION=1.1.1
NATIVE_STT_CTRANSLATE2_SOURCE_REF=226c95d94e660c48b11c62e108886b7ef76d589d
NATIVE_STT_CT2_PREFIX=/home/christopherbailey/stt-native-lab/ct2-prefix
PYTHONPATH=/home/christopherbailey/homelab-llm/services/voice-gateway/src
LD_LIBRARY_PATH=/home/christopherbailey/stt-native-lab/ct2-prefix/lib
HF_HOME=/srv/ssd/cache/huggingface
HF_HUB_DISABLE_TELEMETRY=1
PYTHONNOUSERSITE=1
```

Required systemd unit (`/etc/systemd/system/voice-gateway-native-stt.service`):

```ini
[Unit]
Description=Voice Gateway Native STT Wrapper
After=network.target

[Service]
Type=simple
User=christopherbailey
EnvironmentFile=/etc/voice-gateway/native-stt.env
ExecStart=/home/christopherbailey/stt-native-lab/bin/python -m voice_gateway.native_stt_service
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

### Gate 1 checks
```bash
curl -fsS http://127.0.0.1:18081/health | jq .
curl -fsS http://127.0.0.1:18081/health/readiness | jq .

# 5 consecutive short-fixture transcriptions
for i in 1 2 3 4 5; do
  curl -fsS http://127.0.0.1:18081/transcribe \
    -H 'Content-Type: audio/wav' \
    --data-binary @/tmp/stt-cert.wav | jq -c .
done

# 1 longer clip (preferred) with fixture fallback
test -f /tmp/stt-long.wav && LONG_FIXTURE=/tmp/stt-long.wav || LONG_FIXTURE=/tmp/stt-cert.wav
curl -fsS http://127.0.0.1:18081/transcribe \
  -H 'Content-Type: audio/wav' \
  --data-binary @"${LONG_FIXTURE}" | jq .
```

Gate 1 pass criteria:
- readiness proves pinned versions/model/device/compute and `cuda_device_count >= 1`
- all 6 transcription requests succeed
- readiness or startup logs prove one model load reused across all requests (`load_count=1`)

### Gate 2 STT routing switch
Add only STT backend override in voice-gateway env:

```dotenv
VOICE_STT_BACKEND_API_BASE=http://127.0.0.1:18081
```

Request/response translation in Gate 2:
- external request (unchanged): OpenAI-style multipart at `/v1/audio/transcriptions`
- internal call: raw audio bytes to `POST /transcribe` with optional `language` and `prompt`
- wrapper response: JSON `{ "text": "..." }`
- external response mapping:
  - `response_format=json`, `response_format=verbose_json`, or unset -> JSON `{ "text": "..." }`
  - `response_format=text` -> `text/plain`
  - other formats -> HTTP 400 (`unsupported_response_format`) for this first pass

## Direct Orin smoke
```bash
curl -fsS http://192.168.1.93:18080/health
curl -fsS http://192.168.1.93:18080/health/readiness | jq .
curl -fsS http://192.168.1.93:18080/v1/models -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq .
curl -fsS http://192.168.1.93:18080/v1/speakers -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq .
curl -fsS http://192.168.1.93:18080/v1/audio/speech \
  -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"Homelab speech canary.","voice":"alloy","response_format":"wav","speed":1.0}' \
  --output /tmp/voice-gateway-canary.wav
curl -fsS http://192.168.1.93:18080/v1/audio/transcriptions \
  -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" \
  -F 'file=@/tmp/voice-gateway-canary.wav' \
  -F 'model=whisper-1'

# TTS no-regression check after STT wrapper switch
curl -fsS http://192.168.1.93:18080/v1/audio/speech \
  -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"TTS no-regression check.","voice":"alloy","response_format":"wav","speed":1.0}' \
  --output /tmp/voice-gateway-tts-regression.wav
```

## LiteLLM canary smoke
```bash
curl -fsS http://127.0.0.1:4000/v1/audio/speech \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"voice-tts-canary","input":"Homelab speech canary.","voice":"alloy","response_format":"wav","speed":1.0}' \
  --output /tmp/litellm-voice-canary.wav

curl -fsS http://127.0.0.1:4000/v1/audio/transcriptions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -F 'file=@/tmp/litellm-voice-canary.wav' \
  -F 'model=voice-stt-canary'
```

## Voice alias verification
- `default` and `alloy` must resolve to the same configured backend voice for the
  initial canary.
- Unknown voice behavior must match config:
  - default: HTTP 400
  - optional: deterministic fallback plus warning log

## Open WebUI post-restart verification
After any Open WebUI restart tied to the speech rollout:
- verify `ENABLE_PERSISTENT_CONFIG=False`
- verify effective `AUDIO_STT_*` and `AUDIO_TTS_*` envs from systemd
- verify the Admin UI audio page reflects the same values after restart
- verify one real voice turn lands on LiteLLM `voice-*-canary` aliases

Suggested commands:
```bash
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '\n' | rg '^"?ENABLE_PERSISTENT_CONFIG=False$'
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '\n' | rg '^"?AUDIO_(STT|TTS)_'
curl -fsS http://127.0.0.1:3000/health | jq .
```

## Diarization promotion gate
Do not promote diarization-capable enriched transcription responses until an
end-to-end test proves the chosen response format survives the LiteLLM/OpenAI-compatible
transcription path without breaking clients.
