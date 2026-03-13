# Voice Gateway

Voice Gateway is the homelab’s **voice I/O service** designated for deployment
on the Orin. A live deployment is not documented yet.

Phase 1 is intentionally narrow:
- XTTS-v2 text-to-speech only
- local CLI smoke path
- localhost-only HTTP wrapper
- WAV-only output
- no STT
- no LiteLLM runtime calls
- no cloned voice enrollment

Current status:
- XTTS runtime proof is closed in the repo-tracked proof container.
- XTTS model materialization and first one-shot synth are closed on the Orin.
- B6 localhost wrapper proof is also closed:
  - thin wrapper-proof image built from the proven runtime
  - `GET /health` and `GET /health/readiness` succeeded on localhost
  - one localhost `POST /v1/audio/speech` returned a valid WAV
  - the returned WAV played successfully through the approved Kiwi DAC sink
- `Containerfile.wrapper-proof` is the canonical local TTS wrapper runtime path for current proof and integration work.
- The next intended consumer is Open WebUI TTS on the Mini through a Mini-local SSH forward to the Orin loopback wrapper, not a new LAN bind.
- The next step is above the XTTS bootstrap layer, not another runtime-recovery loop.

Start here:
- `SERVICE_SPEC.md` (contracts, env)
- `RUNBOOK.md` (operations)
