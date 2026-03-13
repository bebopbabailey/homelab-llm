# Voice Gateway — RUNBOOK

## Current Status
- Voice Gateway is not documented as deployed on the Orin yet.
- XTTS runtime/materialization/synth proof is closed on Orin.
- B6 localhost wrapper proof is also closed.

## Phase 1 Scope
- XTTS-v2 text-to-speech only
- local CLI smoke path
- localhost-only HTTP wrapper
- no STT
- no LiteLLM runtime calls
- no cloned voice enrollment

## Preflight Blocker
- Do not trust the current scaffold until the repo-tracked recovery runtime is
  proven on Orin.
- The abandoned host-native old-`TTS` bootstrap path is superseded.
- Keep the repo as the source of truth.
- The next runtime proof must come from a repo-tracked container build, not an
  interactive snowflake environment.
- Do not trigger the first XTTS model download during bootstrap proof.
- Current observed failures:
  - `TTS==0.22.0` pulled `spacy[ja] -> sudachipy` and failed without a Rust compiler.
  - `TTS==0.20.0` avoided that chain but still failed building
    `TTS/tts/utils/monotonic_align/core.c`.
  - Generic PyPI `torchaudio==2.8.0` would install generic `torch==2.8.0` and
    replace the NVIDIA-provided `torch==2.8.0a0+5228986c39.nv25.06`.
  - Current proof image state shows `transformers==5.3.0`, and
    `from TTS.api import TTS` fails because `transformers>=5.1` is currently
    broken for `coqui-tts`. The temporary compatibility line is `5.0.x`.

## Active Recovery Direction
- Use the NVIDIA Jetson PyTorch base image path that matches the Orin host's
  actual Jetson Linux / L4T line and CUDA userspace.
- Current verified proof base image: `nvcr.io/nvidia/pytorch:25.06-py3-igpu`.
- Diagnostic note: `25.06-py3-igpu` is newer than the host JetPack 6.2 / CUDA
  12.6 generation. If the B3 import/CUDA probe fails, treat base-image / host
  compatibility as the first suspect, not the Voice Gateway app code.
- Install the maintained `coqui-tts` package inside that container runtime.
- Keep the Voice Gateway CLI and localhost wrapper code in the repo and build
  the runtime image from the repo.
- Do not hide the service logic in an ad hoc container image.
- Do not codify dependency pins or a lockfile until the container import gate
  succeeds on Orin.

## Baseline Checks
- Confirm Orin identity and current host status using `docs/foundation/orin-agx.md`.
- Run the Orin verification commands in `docs/foundation/testing.md`.
- Verify speaker output tools are present.

## Canonical Local TTS Runtime Path
- `Containerfile.runtime-proof` is the engine/runtime baseline.
- `Containerfile.wrapper-proof` is the canonical local TTS wrapper runtime path for current proof and integration work.
- Runtime base image is digest-pinned:
  - `nvcr.io/nvidia/pytorch:25.06-py3-igpu@sha256:90f3c17838fde28d5c7ae2d5bfbc8a4c587d3797767ea96cdd48fe82e3613f3b`
- Approved SSD-backed host paths:
  - model cache root: `/srv/ssd/models/voice-gateway`
  - Hugging Face cache root: `/srv/ssd/cache/huggingface`
  - output root: `/srv/ssd/outputs/voice-gateway`

## Canonical Local Smoke Sequence
1. Start `voice-gateway-wrapper-proof:local` on Orin with:
   - container bind `0.0.0.0`
   - Docker publish `127.0.0.1:18080:18080`
   - no host networking
2. Verify `GET /health`
3. Verify `GET /health/readiness`
4. Verify `GET /v1/speakers`
5. Verify one `POST /v1/audio/speech`
6. Validate the returned WAV under `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`
7. Optionally smoke test playback through the Kiwi DAC sink

Cold-path note:
- `GET /health/readiness` and `GET /v1/speakers` can take about `60-90s` on a cold path.
- Use longer curl timeouts for readiness/speakers checks instead of assuming warm-cache behavior.

## Orin Baseline Checks
```bash
ssh orin 'test -x /home/christopherbailey/.local/bin/uv && /home/christopherbailey/.local/bin/uv --version'
ssh orin 'python3 --version'
ssh orin 'df -h'
```

## Superseded Commands
- Do not run the old host-native `uv sync --extra xtts` path from earlier notes.
- Do not assume `/home/christopherbailey/homelab-llm/layer-interface/voice-gateway`
  exists on Orin; current docs must stay relative to the repo checkout or the
  repo-tracked container build context.

## B3 Import/CUDA Proof
- Add the repo-tracked proof build file:
  - `layer-interface/voice-gateway/Containerfile.runtime-proof`
- Stage the current service subtree to `/tmp/voice-gateway-runtime-proof` on
  Orin when a persistent repo checkout is not present there.
- Rebuild the proof image on Orin if it is absent after storage correction:
```bash
tar -C /home/christopherbailey/homelab-llm/layer-interface/voice-gateway -cf - . \
  | ssh orin 'rm -rf /tmp/voice-gateway-runtime-proof && mkdir -p /tmp/voice-gateway-runtime-proof && tar -C /tmp/voice-gateway-runtime-proof -xf -'

ssh orin 'cd /tmp/voice-gateway-runtime-proof && sudo docker build -f Containerfile.runtime-proof -t voice-gateway-xtts-proof:local .'
```
- The proof image is runtime-only:
  - base image: `nvcr.io/nvidia/pytorch:25.06-py3-igpu`
  - package install: `coqui-tts==0.27.5`
  - explicit compatibility pin: `transformers==5.0.0`
  - pinned torchaudio source ref: `v2.8.0`
  - pinned torchaudio source commit:
    `6e1c7fe9ff6d82b8665d0a46d859d3357d2ebaaa`
  - extra Python package: `soundfile`
  - extra OS packages:
    - `libsndfile1`
    - `ffmpeg`
    - `libavformat-dev`
    - `libavcodec-dev`
    - `libavutil-dev`
    - `libavdevice-dev`
    - `libavfilter-dev`
- Official torchaudio Jetson/source-build prerequisites already present in the
  base image:
  - `git`
  - `cmake`
  - `ninja`
  - `gcc`
  - `g++`
- Recovered torchaudio path:
  - keep the NVIDIA torch build untouched
  - do not `pip install torchaudio` from generic PyPI
  - source-build torchaudio from the pinned `v2.8.0` ref against the existing
    NVIDIA torch with `USE_CUDA=1`
  - install the resulting wheel with `--no-deps`
- Recovered Coqui path:
  - keep NVIDIA `torch` and the source-built `torchaudio` untouched
  - explicitly pin `transformers==5.0.0`
  - reason:
    - current upstream guidance is that `transformers>=5.1` is broken for
      `coqui-tts` right now
    - the temporary compatibility line is `5.0.x`
- Do not copy the Voice Gateway wrapper code into the proof image.
- Before rerunning the full B3 probe, run one quick package-sanity check:
```bash
ssh orin 'sudo docker run --rm --runtime nvidia --gpus all --network none voice-gateway-xtts-proof:local bash -lc '\''python3 -m pip show transformers coqui-tts tokenizers huggingface-hub'\'''
```
- Probe the runtime with GPU exposure enabled and network disabled:
```bash
ssh orin 'sudo docker run --rm --runtime nvidia --gpus all --network none voice-gateway-xtts-proof:local python3 - <<\"PY\"
import json
from importlib import metadata

import soundfile
import torch
import torchaudio
import transformers
from TTS.api import TTS

try:
    cudnn_version = torch.backends.cudnn.version()
except Exception:
    cudnn_version = None

payload = {
    \"coqui_tts_package_version\": metadata.version(\"coqui-tts\"),
    \"coqui_python_import\": \"from TTS.api import TTS\",
    \"transformers_version\": transformers.__version__,
    \"torch\": torch.__version__,
    \"torchaudio\": torchaudio.__version__,
    \"soundfile\": soundfile.__version__,
    \"torch_cuda_version\": torch.version.cuda,
    \"cudnn_version\": cudnn_version,
    \"cuda_available\": torch.cuda.is_available(),
    \"cuda_device_count\": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    \"cuda_device_name\": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY'
```
- The maintained package name is `coqui-tts`, but the expected Python import
  namespace for the probe is `from TTS.api import TTS`.
- Do not instantiate `TTS(...)`, enumerate models, synthesize audio, or touch
  the HTTP wrapper in B3.
- Carry-forward warning:
  - the proof image currently uses Python `3.12`
  - if B3 succeeds, later wrapper/container integration must reconcile that
    with the service project's declared Python requirements before copying
    wrapper code into the image

## Stop Gate
- Stop after the import/CUDA probe result is known.
- Do not run `voice-gateway list-speakers`, `voice-gateway synth`, or the HTTP
  smoke in B3.
- Do not trigger XTTS model download.

## B4 Model-Download Gate
- B4 is storage/cache inspection and command documentation only.
- Do not trigger the first XTTS model pull in B4.
- Current Orin findings:
  - `/` free space: about `31G`
  - `/srv/ssd` free space: about `1.7T`
  - Docker root: `/srv/ssd/containers/docker`
  - containerd root: `/srv/ssd/containers/containerd`
  - proof image size: about `5.35GB`
  - host cache root `/srv/ssd/cache/huggingface` exists and is writable
  - `/srv/ssd/models/voice-gateway` exists and is writable
  - `/srv/ssd/outputs/voice-gateway` exists and is writable
- B4 closure criteria are now satisfied.
- Approved later model cache root:
  - `/srv/ssd/models/voice-gateway`
- Approved later XTTS materialization path:
  - `/srv/ssd/models/voice-gateway/tts/tts_models--multilingual--multi-dataset--xtts_v2`
- Approved later output root:
  - `/srv/ssd/outputs/voice-gateway`
- Approved later first-synth host output path:
  - `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`
- Approved later first-synth container output path:
  - `/output/voice-gateway-phase1.wav`
- Approved later model-init-only command for B5 approval:
```bash
ssh orin 'sudo docker run --rm \
  --runtime=nvidia \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -e TTS_HOME=/model-cache \
  -e HF_HOME=/hf-cache \
  -e COQUI_TOS_AGREED=1 \
  -v /srv/ssd/models/voice-gateway:/model-cache \
  -v /srv/ssd/cache/huggingface:/hf-cache \
  voice-gateway-xtts-proof:local python3 - <<\"PY\"
from TTS.api import TTS
tts = TTS(\"tts_models/multilingual/multi-dataset/xtts_v2\", progress_bar=True)
PY'
```
- Do not add `.to("cuda")` to that command in B4. GPU placement belongs to B5.
- Validation command used to close B4:
```bash
ssh orin 'sudo sh -lc '\''
for p in \
  /srv/ssd/models/voice-gateway \
  /srv/ssd/cache/huggingface \
  /srv/ssd/outputs/voice-gateway; do
    echo "== $p ==";
    if [ -d "$p" ]; then echo exists=yes; else echo exists=no; fi;
    if [ -w "$p" ]; then echo writable=yes; else echo writable=no; fi;
    ls -ld "$p" 2>/dev/null || true;
  done
'\'''
```
- B4 is now closed. Do not run the approved model-init-only command until B5 is
  explicitly approved.

## B5 First Materialization And One-Shot Synth
- B5 is now complete.
- XTTS-v2 materialized successfully in the proof container with SSD-backed host
  mounts:
  - model cache root: `/srv/ssd/models/voice-gateway`
  - Hugging Face cache root: `/srv/ssd/cache/huggingface`
  - output root: `/srv/ssd/outputs/voice-gateway`
- Materialized XTTS path on Orin:
  - `/srv/ssd/models/voice-gateway/tts/tts_models--multilingual--multi-dataset--xtts_v2`
- Verified materialized files:
  - `model.pth`
  - `config.json`
  - `vocab.json`
  - `hash.md5`
  - `speakers_xtts.pth`
- Preset speaker inspection succeeded:
  - `speakers_count=58`
  - `selected_speaker=Aaron Dreschner`
  - `en_available=true`
- First one-shot synth command succeeded with:
  - text: `Phase one voice gateway check.`
  - language: `en`
  - speaker: `Aaron Dreschner`
- Output artifact:
  - host path: `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`
  - container path: `/output/voice-gateway-phase1.wav`
- Output validation:
  - file size: `186956` bytes (`183K`)
  - channels: `1`
  - sample width: `2`
  - frame rate: `24000`
  - frames: `93456`
  - duration: about `3.894s`
- B5 stop gate is satisfied:
  - no wrapper/HTTP work was run
  - no STT work was run
  - no LiteLLM runtime call was made
- Next gate:
  - B6 localhost wrapper proof only
  - do not reopen model-materialization or synth troubleshooting unless B6
    reveals a wrapper-specific issue

## B6 Localhost Wrapper Proof
- Build a thin wrapper-proof image from `voice-gateway-xtts-proof:local`.
- Keep the XTTS runtime inside the proven container boundary.
- Install the project’s existing lightweight wrapper deps from repo metadata:
  - `fastapi`
  - `httpx`
  - `pydantic`
  - `uvicorn`
- Run a no-start import smoke before boot:
```bash
ssh orin 'sudo docker run --rm \
  --runtime=nvidia \
  --gpus all \
  --network none \
  voice-gateway-wrapper-proof:local \
  python3 - <<\"PY\"
import voice_gateway.api
import voice_gateway.service
import voice_gateway.cli
print("WRAPPER_IMPORT_OK")
PY'
```
- Start the wrapper with container-local bind `0.0.0.0` and host-local port publish `127.0.0.1:18080:18080`.
- Use approved SSD-backed mounts:
  - `/srv/ssd/models/voice-gateway -> /model-cache`
  - `/srv/ssd/cache/huggingface -> /hf-cache`
  - `/srv/ssd/outputs/voice-gateway -> /output`
- Verify:
  - `GET /health`
  - `GET /health/readiness`
  - one localhost `POST /v1/audio/speech`
- Save the returned WAV to:
  - `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`
- Smoke test playback of that returned WAV through:
  - preferred sink: `alsa_output.usb-Kiwi_Ears_Kiwi_Ears-Allegro_Mini_2020-02-20-0000-0000-0000-00.analog-stereo`
  - fallback ALSA device: `plughw:3,0`
- Do not use host networking.
- Do not widen into STT, LiteLLM runtime calls, LAN/public bind, or systemd in B6.
- B6 is now complete.
- Observed B6 results on Orin:
  - thin wrapper-proof image built successfully from the proven runtime image
  - wrapper import smoke returned `WRAPPER_IMPORT_OK`
  - wrapper served successfully on `127.0.0.1:18080` via loopback-only Docker publish
  - `GET /health` returned HTTP `200` with JSON
  - `GET /health/readiness` returned HTTP `200` with ready-state JSON
  - one localhost `POST /v1/audio/speech` returned a valid WAV
  - returned WAV path: `/srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav`
  - returned WAV validation:
    - non-empty
    - `24000 Hz`
    - mono
    - about `3.937s`
  - one playback smoke succeeded through the Kiwi DAC sink using explicit sink targeting
- After B6:
  - do not reopen XTTS bootstrap recovery unless a later integration reveals a concrete regression
  - move the next task above the runtime/bootstrap layer

## Open WebUI TTS Proof Path
- Current next consumer: Open WebUI on the Mini.
- Keep Voice Gateway loopback-only on Orin.
- Use a Mini-local SSH forward instead of widening the service bind:
```bash
ssh -fN -o ExitOnForwardFailure=yes -L 127.0.0.1:18081:127.0.0.1:18080 orin
```
- Forwarded TTS base URL:
  - `http://127.0.0.1:18081/v1`
- Forwarded verification sequence:
```bash
curl -fsS http://127.0.0.1:18081/health
curl -m 180 -fsS http://127.0.0.1:18081/health/readiness
curl -m 180 -fsS http://127.0.0.1:18081/v1/speakers
curl -fsS \
  -H "Content-Type: application/json" \
  -d '{"model":"xtts-v2","input":"Phase one voice gateway check.","voice":"default","response_format":"wav","language":"en"}' \
  http://127.0.0.1:18081/v1/audio/speech \
  --output /tmp/openwebui-tts-smoke.wav
```
- Verified forwarded behavior:
  - `/health` succeeded
  - `/health/readiness` succeeded
  - `/v1/speakers` succeeded
  - one forwarded `POST /v1/audio/speech` returned a valid WAV
- Installed Open WebUI build exposes dedicated TTS config fields:
  - `AUDIO_TTS_ENGINE`
  - `AUDIO_TTS_OPENAI_API_BASE_URL`
  - `AUDIO_TTS_OPENAI_API_KEY`
  - `AUDIO_TTS_MODEL`
  - `AUDIO_TTS_VOICE`
  - `AUDIO_TTS_OPENAI_PARAMS`
  - `AUDIO_TTS_SPLIT_ON`
- Current target values for TTS-only proof use:
  - `AUDIO_TTS_ENGINE=openai`
  - `AUDIO_TTS_OPENAI_API_BASE_URL=http://127.0.0.1:18081/v1`
  - `AUDIO_TTS_OPENAI_API_KEY=voice-gateway-local-dev`
  - `AUDIO_TTS_MODEL=xtts-v2`
  - `AUDIO_TTS_VOICE=default`
  - `AUDIO_TTS_OPENAI_PARAMS={}`
- Current `/etc/open-webui/env` does not yet set any `AUDIO_TTS_*` variables.
- Keep the global LiteLLM/OpenAI config untouched. Do not repoint `OPENAI_API_BASE_URL` / `OPENAI_API_KEY` for TTS.

## Manual Voice Audition Plan
1. Verify `/v1/speakers`
2. Use `default` plus the first 5 non-default voice IDs sorted alphabetically
3. Use the same phrase for every sample:
   - `Hello. This is the homelab assistant voice comparison sample.`
4. Save samples under:
   - `/srv/ssd/outputs/voice-gateway/audition/<voice>.wav`
5. Play each sample through the Kiwi DAC sink:
```bash
paplay --device=alsa_output.usb-Kiwi_Ears_Kiwi_Ears-Allegro_Mini_2020-02-20-0000-0000-0000-00.analog-stereo <file>
aplay -D plughw:3,0 <file>
```
6. Rank each voice for:
   - clarity
   - warmth
   - naturalness
   - assistant-style delivery

## Local CLI Smokes
Run these only after bootstrap proof succeeds and XTTS model download is
explicitly approved.
```bash
/home/christopherbailey/.local/bin/uv run voice-gateway list-speakers
/home/christopherbailey/.local/bin/uv run voice-gateway synth --text "phase one voice gateway check" --voice default --language en --out /srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav
/home/christopherbailey/.local/bin/uv run voice-gateway synth --text "playback check" --voice default --language en --out /srv/ssd/outputs/voice-gateway/voice-gateway-phase1.wav --play
```

## Localhost HTTP Smoke
Run this only after bootstrap proof succeeds and XTTS model download is
explicitly approved.
Start serve mode only with an explicit localhost port:
```bash
/home/christopherbailey/.local/bin/uv run voice-gateway-service --port <local-port>
# or
/home/christopherbailey/.local/bin/uv run voice-gateway serve --port <local-port>
```

Then verify:
```bash
curl -s http://127.0.0.1:<local-port>/health
curl -s http://127.0.0.1:<local-port>/health/readiness
curl -s http://127.0.0.1:<local-port>/v1/speakers
```

## Common Issues

### Mic not detected
- Check `lsusb`
- Check `arecord -l`
- Set `AUDIO_INPUT_DEVICE`

### No audio output
- Check default sink
- Verify `paplay` / `aplay`
- Re-run the CLI smoke without `--play` to isolate synthesis from playback

### TTS fails
- Confirm the repo-tracked container build succeeded on Orin
- If torchaudio source-build is the current blocker, inspect the proof image's
  torch version and build tools first, then rebuild only after the pinned
  torchaudio source ref and FFmpeg development packages are in place
- If `from TTS.api import TTS` fails while `torch` and `torchaudio` imports
  already pass, inspect the proof image's `transformers` version next
- If the rebuild or the import/CUDA probe fails, treat base-image / host
  compatibility as the first suspect before touching app code
- Do not proceed to synthesis, model-load, or wrapper debugging until the probe passes

### Unknown voice
- Run `voice-gateway list-speakers`
- Confirm the requested voice resolves through built-in discovery/config policy

## Logs
- Default: stdout
- Optional JSONL file sink via `VOICE_LOG_PATH`
- Each entry includes discovery, synth, WAV write, and optional playback timings.
