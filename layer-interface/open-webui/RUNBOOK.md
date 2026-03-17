# Runbook: Open WebUI

## Start/stop
```bash
sudo systemctl start open-webui.service
sudo systemctl stop open-webui.service
sudo systemctl restart open-webui.service
```

## Logs
```bash
journalctl -u open-webui.service -f
```

## Config authority
`ENABLE_PERSISTENT_CONFIG=False` makes systemd env/drop-ins authoritative.
Admin UI edits to env-backed audio settings are session-only and must not survive restart.

## Canonical speech canary env
```dotenv
AUDIO_STT_ENGINE=openai
AUDIO_STT_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1
AUDIO_STT_OPENAI_API_KEY=<litellm-key>
AUDIO_STT_MODEL=voice-stt-canary

AUDIO_TTS_ENGINE=openai
AUDIO_TTS_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1
AUDIO_TTS_OPENAI_API_KEY=<litellm-key>
AUDIO_TTS_MODEL=voice-tts-canary
AUDIO_TTS_VOICE=alloy
AUDIO_TTS_OPENAI_PARAMS={}
```

Keep the global LiteLLM OpenAI settings unchanged.

## Post-restart UI-state verification
Run this after every Open WebUI restart during canary and before promotion:

```bash
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '\n' | rg '^"?ENABLE_PERSISTENT_CONFIG=False$'
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '\n' | rg '^"?AUDIO_STT_'
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '\n' | rg '^"?AUDIO_TTS_'
curl -fsS http://127.0.0.1:3000/health | jq .
```

Then verify in the Admin UI audio page after restart:
- STT engine shows `openai`
- STT model shows `voice-stt-canary`
- TTS engine shows `openai`
- TTS model shows `voice-tts-canary`
- TTS voice shows `alloy`

Promotion is blocked if the restarted UI shows stale audio settings that do not
match the env-driven values.

## End-to-end voice canary
- restart Open WebUI
- open the UI and complete one voice turn
- confirm LiteLLM logs show `voice-stt-canary` and `voice-tts-canary`
- confirm no direct Orin URL is configured in Open WebUI audio settings
