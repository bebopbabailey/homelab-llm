# Voice Gateway — ARCHITECTURE

## Why This Exists
The homelab needs a durable speech boundary on the Orin while keeping LiteLLM as
the only client-facing gateway. `voice-gateway` owns that boundary.

## Canonical topology
- Open WebUI talks to LiteLLM on the Mini.
- LiteLLM routes speech aliases directly to the Orin `voice-gateway` LAN `/v1` endpoint.
- `voice-gateway` calls localhost-only Speaches on the Orin for STT/TTS.
- Speaches preloads the chosen canary STT and Kokoro TTS models and keeps them warm.

## Responsibilities
- `voice-gateway`
  - stable OpenAI-compatible speech facade
  - external model alias mapping
  - external voice alias mapping
  - repo-canonical curated TTS registry (`registry/tts_models.jsonl`)
  - structured request logging and readiness checks
  - local operator dashboard (`/ops`) for model discovery/lifecycle and TTS audition
  - CLI-first control plane (`voicectl`) over supported `/ops/api/*` routes
  - manual promotion-plan generation for root-owned config changes
  - deploy provenance visibility through optional manifest file
  - future diarization orchestration
- Speaches
  - faster-whisper STT
  - Kokoro TTS
  - warm-model appliance behavior
  - localhost-only backend implementation

## Boundary rules
- LiteLLM remains the only client-facing gateway.
- Open WebUI never calls the Orin directly.
- Speaches is an internal implementation detail behind `voice-gateway`.
- Diarization must not enter the default Open WebUI voice-turn critical path.
- `/ops` does not bypass `voice-gateway` public speech contract and does not auto-write
  root-owned runtime files under `/etc`.
- remote Speaches registry is discovery data only; curated repo registry is the
  operator source of truth.

## Voice policy
- External voices `default` and `alloy` map to the same initial Kokoro backend voice.
- Unknown voices either reject with HTTP 400 or fall back deterministically with a warning log.
- Current default policy is strict reject unless config explicitly enables fallback.

## Diarization gate
- Diarization is a required deliverable, but promotion is blocked until an enriched
  transcription response format is proven end-to-end through the LiteLLM/OpenAI-compatible
  transcription path without breaking clients.
