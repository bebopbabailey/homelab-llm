# Voice Gateway — RUNBOOK

## Start / Stop
- Start via systemd on the Orin (preferred) or CLI in a tmux session.
- Verify microphone device is present before starting.

## Health Checks
If the service exposes HTTP health:
- On Orin: `curl -s http://127.0.0.1:<port>/health`
- From Mini (connectivity check): `curl -s http://192.168.1.93:<port>/health`

Otherwise:
- confirm process is running
- confirm log file is being written on each activation

## Common Issues

### Mic not detected
- Check `lsusb`
- Check `arecord -l`
- Set `AUDIO_INPUT_DEVICE`

### No audio output
- Check default sink
- Set `AUDIO_OUTPUT_DEVICE`
- Verify with a simple tone playback test

### STT slow / inaccurate
- Confirm model size
- Confirm CPU load
- Reduce sample rate / chunking
- Consider swapping STT backend (but only after logging)

### LiteLLM unavailable
- Check gateway health endpoint
- Confirm base URL
- Confirm model alias exists and routes correctly

### TTS fails
- Verify voice assets installed
- Validate TTS backend binary/path
- Fall back to console output for debugging

## Logs
- Default: `/var/log/voice-gateway/voice.jsonl`
- Each entry includes stage timings and error codes.
