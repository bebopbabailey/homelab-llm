# Tasks: voice-gateway

## Phase 1
- Correct service policy docs so local STT/TTS engines are allowed and LiteLLM
  remains the sole future LLM path.
- Remove the abandoned host-native XTTS bootstrap contract from active docs and
  packaging.
- Add `Containerfile.runtime-proof` using the verified NVIDIA Jetson PyTorch
  base image `nvcr.io/nvidia/pytorch:25.06-py3-igpu`.
- Inspect the current proof image and confirm:
  - NVIDIA torch is present
  - `coqui-tts` is installed
  - `torchaudio` is installed
  - `transformers>=5.1` is currently present
- Keep the torchaudio source-build recovery intact.
- Pin `transformers==5.0.0` in the proof image.
- Reason:
  - current upstream guidance is that `transformers>=5.1` is broken for
    `coqui-tts` right now
  - the temporary compatibility line is `5.0.x`
- Rebuild `voice-gateway-xtts-proof:local` on Orin from a staged copy of the
  current service subtree.
- Run a package-sanity check for `transformers`, `coqui-tts`, `tokenizers`, and
  `huggingface-hub` before the full B3 probe.
- Run the B3 import/CUDA probe with `--runtime nvidia --gpus all --network none`.
- Confirm imports for `torch`, `torchaudio`, `soundfile`, and the maintained
  `coqui-tts` Python entrypoint (`from TTS.api import TTS`).
- Confirm `torch.cuda.is_available()` returns `True`.
- Stop after the probe result.
- Stop before first XTTS model download.
- B4 gate:
  - inspect Orin storage and current cache state
  - confirm Docker root and containerd root remain on `/srv/ssd`
  - confirm `/srv/ssd/cache/huggingface` exists and is writable
  - confirm `/srv/ssd/models/voice-gateway` exists and is writable
  - confirm `/srv/ssd/outputs/voice-gateway` exists and is writable
  - document the later model-init-only command against those approved paths
  - document the later first-synth output path
  - stop before first XTTS model download

## Current Gate
- Runtime/bootstrap blocker is closed.
- B4 is closed.
- B5 is closed.
- B6 is closed.
- Canonical local TTS runtime path is `Containerfile.wrapper-proof` on top of the proven runtime image.
- `/v1/speakers` is a verified part of the local proof contract.
- Mini-local SSH forwarding to Orin loopback is the minimum proven consumer reachability path.
- XTTS model materialization succeeded under `/srv/ssd/models/voice-gateway/tts/tts_models--multilingual--multi-dataset--xtts_v2`.
- First one-shot synth succeeded with preset speaker `Aaron Dreschner`.
- Output artifact:
  - `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`
- Output validation:
  - non-empty WAV
  - `24000 Hz`
  - mono
  - about `3.894s`
- B6 wrapper proof result:
  - thin wrapper-proof image built from `voice-gateway-xtts-proof:local`
  - wrapper imports succeeded before boot
  - wrapper started with container-local bind `0.0.0.0` and host-local publish `127.0.0.1:18080:18080`
  - `GET /health` succeeded
  - `GET /health/readiness` succeeded
  - one localhost `POST /v1/audio/speech` succeeded
  - returned WAV saved to `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`
  - Kiwi DAC playback smoke succeeded
- The next gated action is TTS-only consumption above the XTTS bootstrap layer.
- Current hardening/integration items:
  - digest-pin the NVIDIA runtime base image used by `Containerfile.runtime-proof`
  - keep wrapper-proof as the canonical local TTS wrapper runtime path
  - document the canonical local smoke sequence with `/v1/speakers`
  - document the Mini-local SSH forward path for Open WebUI TTS proof
  - document the dedicated Open WebUI `AUDIO_TTS_*` settings and keep global LiteLLM/OpenAI settings untouched
- Next gated action:
  - Open WebUI TTS-only proof on the Mini using the dedicated `AUDIO_TTS_*` settings and the Mini-local SSH forward to the Orin loopback wrapper
- Historical failure evidence retained for traceability:
  - `TTS==0.22.0` failed on `sudachipy` / missing Rust compiler.
  - `TTS==0.20.0` failed building `monotonic_align/core.c`.
  - Generic PyPI `torchaudio==2.8.0` would replace NVIDIA's custom
    `torch==2.8.0a0+5228986c39.nv25.06`.
  - An earlier proof image state had `transformers==5.3.0`, which was outside
    the temporary `coqui-tts` compatibility line of `5.0.x`.
  - If the `transformers==5.0.0` recovery still fails under `25.06-py3-igpu`,
    treat base-image / host compatibility as the first suspect.

## Deferred
- STT
- LiteLLM orchestration
- cloned voices
- reference WAV enrollment
- LAN exposure
