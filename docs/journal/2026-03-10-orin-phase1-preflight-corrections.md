# Orin Phase 1 Preflight Corrections

Date: 2026-03-10

Purpose: append-only correction note for the Orin post-upgrade baseline before
`layer-interface/voice-gateway` Phase 1 implementation. This entry clarifies
tooling and packaging facts that affect the XTTS-v2 TTS-only slice.

## Correction Scope
- This note corrects the tool-check interpretation in
  `docs/journal/2026-03-10-orin-post-upgrade-baseline.md`.
- Treat this entry as the latest dated evidence for Voice Gateway Phase 1
  packaging and preflight assumptions.

## Corrected Tooling Facts
- `uv` is installed at `/home/christopherbailey/.local/bin/uv`.
- Non-interactive shells may omit `~/.local/bin` from `PATH`, so Orin service
  commands must call the explicit `uv` path or export `PATH` first.
- `python3 -m pip` is not available on the host.
- `torch`, `TTS`, `soundfile`, `fastapi`, and `uvicorn` are not installed yet.

## Packaging Implication
- Phase 1 should still use `uv` as the host-managed environment convention.
- The stale `.dev` Jetson package hostname is not the working source for this
  host.
- The working Jetson package source family is
  `https://pypi.jetson-ai-lab.io/jp6/cu126/+simple/`.
- Exact Orin-reachable wheel pins:
  - `torch @ https://pypi.jetson-ai-lab.io/jp6/cu126/+f/62a/1beee9f2f1470/torch-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=62a1beee9f2f147076a974d2942c90060c12771c94740830327cae705b2595fc`
  - `torchaudio @ https://pypi.jetson-ai-lab.io/jp6/cu126/+f/81a/775c8af36ac85/torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=81a775c8af36ac859fb3f4a1b2f662d5fcf284a835b6bb4ed8d0827a6aa9c0b7`
- Orin-side `uv pip install --dry-run` resolved successfully with those wheel
  pins plus `TTS==0.22.0`, `soundfile`, `fastapi`, and `uvicorn`.
- The first real Orin-native `uv sync` using `TTS==0.22.0` failed on
  `sudachipy==0.6.10` because the dependency chain
  `tts -> spacy[ja] -> sudachipy` required a Rust compiler that is not present
  on the host.
- The inspected recovery pin is `TTS==0.20.0`, which avoids the `spacy[ja]`
  dependency in package metadata and resolves cleanly in Orin dry-run.
- The first real Orin-native `uv sync` using `TTS==0.20.0` also failed, this
  time while building `TTS/tts/utils/monotonic_align/core.c` with a NumPy API
  mismatch (`PyArray_Descr` / `subarray`) under build isolation.
- As of this note, the Coqui `TTS` package portion of the XTTS bootstrap remains
  unproven on this Orin even though the Jetson `torch` / `torchaudio` wheel path
  is known.
- Wheel-only install policy is not valid for this stack because `TTS` has no
  usable wheel and requires source build allowance.
- Bootstrap proof remains blocked until the real Orin-native `uv sync`, import
  validation, and `torch.cuda.is_available()` checks succeed.

## Current Voice Gateway Relevance
- Phase 1 acceptance requires successful local XTTS-v2 text-to-speech generation
  only.
- No reference WAV or cloned-voice enrollment is required for Phase 1.
- The localhost-only HTTP wrapper remains in scope, but it is not the hard
  acceptance gate for Phase 1.
- No XTTS model download has happened yet.
- Do not trigger the first XTTS model download without explicit approval after
  the import gate succeeds.

## Recovery Direction Update
- The host-native old-`TTS` bootstrap path is now treated as failed recovery
  evidence, not the active implementation plan.
- The maintained package to validate next is `coqui-tts`, not the old `TTS`
  package.
- The next recovery attempt should use a repo-tracked container build based on
  an NVIDIA `l4t-pytorch` class image that matches the host's actual Jetson
  Linux / L4T line and CUDA userspace.
- The repo remains the source of truth for the Voice Gateway wrapper and build
  inputs; a working container must not become a snowflake.
- No additional XTTS runtime/package claims should be treated as canonical
  until the container build and import gate succeed on Orin.
