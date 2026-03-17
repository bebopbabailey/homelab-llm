# Voice Gateway Demo

This is the quickest way to try the current local Voice Gateway TTS stack on the Orin.

This is **TTS only**, not STT.

This doc assumes you are running commands **directly on the Orin**.

Backend URL:
- `http://127.0.0.1:18080`

Default output path:
- `/srv/ssd/outputs/voice-gateway/...`

## 2. Start the local backend on the Orin
Start the proven wrapper container:

```bash
sudo docker run --rm -d \
  --name voice-gateway-wrapper-proof \
  --runtime=nvidia \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -p 127.0.0.1:18080:18080 \
  --mount type=bind,src=/srv/ssd/models/voice-gateway,dst=/model-cache \
  --mount type=bind,src=/srv/ssd/cache/huggingface,dst=/hf-cache \
  --mount type=bind,src=/srv/ssd/outputs/voice-gateway,dst=/output \
  -e TTS_HOME=/model-cache \
  -e HF_HOME=/hf-cache \
  -e COQUI_TOS_AGREED=1 \
  voice-gateway-wrapper-proof:local \
  python3 -m voice_gateway.service --host 0.0.0.0 --port 18080
```

Stop it when you are done:

```bash
sudo docker stop voice-gateway-wrapper-proof
```

Quick health checks:

```bash
curl -fsS http://127.0.0.1:18080/health
curl -m 180 -fsS http://127.0.0.1:18080/health/readiness
```

## 3. List available voices
Direct API on the Orin:

```bash
curl -m 180 -fsS http://127.0.0.1:18080/v1/speakers
```

Helper script on the Orin:

```bash
~/bin/try-voice --list
```

## 4. Try a sentence interactively
The helper will prompt for text and voice if you do not pass them:

On the Orin:

```bash
~/bin/try-voice
```

If you leave the voice blank, it uses `default`.

## 5. Try a sentence non-interactively
Use a preset voice directly on the Orin:

```bash
~/bin/try-voice --text "Hello from the Orin."
```

Skip playback and just save the WAV:

```bash
~/bin/try-voice --voice default --text "Hello from the Orin." --no-play
```

Save to a custom path:

```bash
~/bin/try-voice \
  --voice default \
  --text "Hello from the Orin." \
  --out /srv/ssd/outputs/voice-gateway/my-test.wav
```

Cycle through available preset voices one by one using the same sentence:

```bash
~/bin/try-voice --cycle --text "Hello from the Orin."
```

The helper will:
- render each voice to its own WAV
- play it
- wait for Enter to continue or `q` to stop

## 6. Where files go
If you do not pass `--out`, the helper chooses the first usable output root:

- `/srv/ssd/outputs/voice-gateway` if it exists and is writable on the Orin
- otherwise `${TMPDIR:-/tmp}/voice-gateway`

Examples:

```text
/srv/ssd/outputs/voice-gateway/voice-demo-<voice>-<timestamp>.wav
/tmp/voice-gateway/voice-demo-<voice>-<timestamp>.wav
```

## 7. Playback behavior
The helper prefers the proven Kiwi DAC sink if it is present:

```text
alsa_output.usb-Kiwi_Ears_Kiwi_Ears-Allegro_Mini_2020-02-20-0000-0000-0000-00.analog-stereo
```

If that sink is not present, it falls back to the default Pulse sink. If
`paplay` is not available, it falls back to `aplay`.

You can force a Pulse sink explicitly:

```bash
~/bin/try-voice \
  --device alsa_output.usb-Kiwi_Ears_Kiwi_Ears-Allegro_Mini_2020-02-20-0000-0000-0000-00.analog-stereo \
  --voice default \
  --text "Hello from the Orin."
```

## 8. What the helper actually calls
The helper uses the current local Voice Gateway backend only:

- `GET /health`
- `GET /v1/speakers`
- `POST /v1/audio/speech`

It does not start containers for you, and it does not change the service
contract.

## 9. Helper installed on the Orin
The primary operator path is the helper deployed on the Orin at:

```text
/home/christopherbailey/bin/try-voice
```

So on the Orin you can run:

```bash
~/bin/try-voice --list
~/bin/try-voice --text "Hello from the Orin." --voice default
~/bin/try-voice --cycle --text "Hello from the Orin."
```

If you are editing the repo on another host, the source copy of the helper lives at:

```text
/home/christopherbailey/homelab-llm/layer-interface/voice-gateway/scripts/try-voice.sh
```
