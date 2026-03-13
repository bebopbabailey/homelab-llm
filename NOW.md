# NOW

Active
- Harden the local Voice Gateway TTS runtime path and document the minimum Open WebUI TTS integration path:
  - digest-pin the NVIDIA runtime base image lineage used by the Orin XTTS proof stack.
  - codify the canonical local smoke sequence, including `/v1/speakers` and the observed cold-path readiness behavior.
  - document the Mini-local SSH forward path and the dedicated Open WebUI `AUDIO_TTS_*` settings for TTS-only proof use.

NEXT UP
- Open WebUI TTS-only proof on the Mini using the dedicated `AUDIO_TTS_*` settings and the Mini-local SSH forward to the Orin loopback wrapper.
