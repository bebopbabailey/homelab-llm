# Orin Small STT Runtime Slice

## Objective
Move Orin transcription toward a cheap default path: native faster-whisper STT
with `small.en`, exposed only through `voice-gateway` and LiteLLM STT aliases.

## Runtime shape
- Orin native STT wrapper: `127.0.0.1:18081`
- Orin speech facade: `192.168.1.93:18080`
- Public STT model: `whisper-1`
- LiteLLM STT aliases: `voice-stt-canary`, `voice-stt`
- Cleanup remains in `task-transcribe` / `task-transcribe-vivid` as a separate
  LLM step.

## Findings
- Orin was reachable as `theorin`.
- `voice-gateway-native-stt.service` was active and already serving
  `Systran/faster-distil-whisper-large-v3` through CUDA/faster-whisper.
- Whole `voice-gateway` readiness was blocked by the TTS/Speaches side, while
  native STT readiness was healthy. The service now has an STT-only health
  endpoint so transcription does not inherit TTS readiness failures.
- `/srv/ssd` had about `1.7T` available before any model-cache work.
- The existing `/srv/ssd/cache/huggingface` path returned input/output errors
  even for `ls`/`stat`, including the Hugging Face token path. The runtime was
  moved to `/home/christopherbailey/.cache/huggingface-small-stt` for this
  slice instead of attempting disk repair.

## Decision
Use `small.en` as the lightweight Orin transcription default. Keep native STT
localhost-only and keep LiteLLM as the client-facing gateway.

## Cleanup state
- Orin deploy checkout was updated in place at
  `/home/christopherbailey/voice-gateway-canary`.
- Backup path before deployment:
  `/home/christopherbailey/orin-small-stt-backup-20260509T215359Z`.
- `voice-gateway-native-stt.service` is ready with model `small.en`.
- `GET http://192.168.1.93:18080/health/stt` reports ready.
- Direct Orin `/v1/audio/transcriptions` smoke returned non-empty transcript
  JSON from `/tmp/stt-smoke.wav`.
- LiteLLM launcher now sources `/etc/homelab-llm/litellm-voice.env` after the
  repo-local `config/env.local` so the correct Orin voice key wins over stale
  local placeholders.
