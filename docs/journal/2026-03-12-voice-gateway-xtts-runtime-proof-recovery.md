# 2026-03-12 — Voice Gateway XTTS runtime-proof recovery on Orin

## Context
- This entry extends the earlier Orin Voice Gateway trail recorded in:
  - `docs/journal/2026-03-10-orin-voice-baseline.md`
  - `docs/journal/2026-03-10-orin-post-upgrade-baseline.md`
  - `docs/journal/2026-03-10-orin-phase1-preflight-corrections.md`
- Voice Gateway Phase 1 remained intentionally narrow throughout this work:
  - XTTS-v2 TTS only
  - localhost-only wrapper later
  - no STT
  - no LiteLLM runtime calls
  - no voice cloning
  - no LAN/public bind
- The goal of this recovery chain was to prove the XTTS runtime stack on the
  Orin without triggering model download, synthesis, or wrapper integration.

## Goal
- Replace the failed host-native XTTS bootstrap path with a repo-tracked proof
  container on the Orin.
- Prove that the container can import the XTTS runtime stack and see CUDA.
- Stop before any XTTS model asset download, synthesis, or localhost HTTP proof.

## Recovery chronology
- The original host-native `uv` + old `TTS` path was attempted first and then
  abandoned as the active path:
  - `TTS==0.22.0` failed through `spacy[ja] -> sudachipy` because Rust was not
    present on the host.
  - `TTS==0.20.0` also failed, this time in `monotonic_align/core.c`.
- The recovery direction changed to a repo-tracked container path based on an
  NVIDIA Jetson PyTorch image.
- A runtime-only proof image was introduced:
  - base image: `nvcr.io/nvidia/pytorch:25.06-py3-igpu`
  - maintained package: `coqui-tts`
  - no wrapper code copied into the image
- Docker/NVIDIA runtime alignment on the host blocked the first B3 attempt:
  - `--runtime=nvidia` was initially unavailable to Docker
  - host runtime configuration was later corrected outside the app scope
- After runtime alignment, the first B3 probe failed because `torchaudio` was
  missing from the proof image.
- Generic PyPI `torchaudio==2.8.0` was explicitly rejected after dry-run:
  - it would have replaced NVIDIA's custom
    `torch==2.8.0a0+5228986c39.nv25.06`
- Torchaudio recovery then moved to source build:
  - added FFmpeg development packages to the image
  - pinned torchaudio source to `v2.8.0`
  - built torchaudio from source against the existing NVIDIA torch
  - installed the resulting wheel with `--no-deps`
- After torchaudio was fixed, the next B3 failure moved higher in the stack:
  - `from TTS.api import TTS` failed with
    `ImportError: cannot import name 'isin_mps_friendly' from transformers.pytorch_utils`
- Inspection showed the rebuilt image had:
  - `transformers==5.3.0`
  - `coqui-tts==0.27.5`
- Based on current upstream guidance:
  - `transformers>=5.1` is broken for `coqui-tts` right now
  - the temporary compatibility line is `5.0.x`
- The proof image was then rebuilt with:
  - `transformers==5.0.0`
- A package-sanity check passed for:
  - `transformers`
  - `coqui-tts`
  - `tokenizers`
  - `huggingface_hub`
- The final B3 import/CUDA probe then succeeded on the Orin.

## Final proven runtime state
- Base image:
  - `nvcr.io/nvidia/pytorch:25.06-py3-igpu`
- Python:
  - `3.12.3`
- Package state:
  - `coqui-tts==0.27.5`
  - `transformers==5.0.0`
  - `tokenizers==0.22.2`
  - `huggingface_hub==1.6.0`
  - `soundfile==0.13.1`
  - `torch==2.8.0a0+5228986c39.nv25.06`
  - `torchaudio==2.8.0a0+6e1c7fe`
- CUDA/runtime state:
  - `torch.version.cuda == 12.9`
  - `torch.backends.cudnn.version() == 91002`
  - `torch.cuda.is_available() == true`
  - `torch.cuda.device_count() == 1`
  - `torch.cuda.get_device_name(0) == "Orin"`

## Validation
Package-sanity check in the rebuilt proof image:
- `transformers 5.0.0`
- `coqui-tts 0.27.5`
- `tokenizers 0.22.2`
- `huggingface_hub 1.6.0`

Final B3 import/CUDA probe output:

```json
{
  "coqui_python_import": "from TTS.api import TTS",
  "coqui_tts_package_version": "0.27.5",
  "cuda_available": true,
  "cuda_device_count": 1,
  "cuda_device_name": "Orin",
  "cudnn_version": 91002,
  "soundfile": "0.13.1",
  "torch": "2.8.0a0+5228986c39.nv25.06",
  "torch_cuda_version": "12.9",
  "torchaudio": "2.8.0a0+6e1c7fe",
  "transformers_version": "5.0.0"
}
```

Validation boundaries:
- `from TTS.api import TTS` imports successfully
- no XTTS model asset download occurred
- no synthesis occurred
- no localhost wrapper or HTTP proof occurred

## Decisions locked in by this recovery
- Keep the proof runtime repo-tracked.
- Keep NVIDIA torch untouched inside the proof image.
- Keep torchaudio source-built against the NVIDIA torch build.
- Keep `transformers==5.0.0` as the current temporary compatibility pin for
  `coqui-tts==0.27.5`.
- Do not treat the proof image as deployment-complete.
- Do not treat model download, synth, or wrapper proof as completed.

## Risks and carry-forward warnings
- The proof image currently uses Python `3.12`.
- Later wrapper/container integration must explicitly reconcile that with the
  service project's declared Python requirements before wrapper code is copied
  into the image.
- The proof base image is newer than the host JetPack 6.2 / CUDA 12.6
  generation, so future failures may still implicate base-image / host
  compatibility before app code.
- Runtime import/CUDA proof is now closed, but XTTS model assets are still not
  downloaded.

## Next steps
- The next gate is explicit approval for the first XTTS model download.
- Only after that gate:
  - first real XTTS synth on Orin
  - later localhost wrapper proof
- Do not treat those later steps as complete based on this entry.
