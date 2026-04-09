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
Audio env still comes from `/etc/open-webui/env`.
Terminal/tool server registrations currently come from the Open WebUI config
API and persist in Open WebUI state.

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

## Open Terminal registrations
Open WebUI currently uses:
- native terminal server: `http://127.0.0.1:8010`
- read-only MCP tool server: `http://127.0.0.1:8011/mcp`

Admin API checks:
```bash
python3 - <<'PY'
import sqlite3, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
headers = {'Authorization': f'Bearer {api_key}'}
for path in ['api/v1/configs/terminal_servers', 'api/v1/configs/tool_servers', 'api/v1/terminals/', 'api/v1/tools/']:
    req = urllib.request.Request(f'http://127.0.0.1:3000/{path}', headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(path, resp.read().decode())
PY
```

## Post-restart UI-state verification
Run this after every Open WebUI restart during canary and before promotion:

```bash
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
