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
The LiteLLM/OpenAI provider connection also persists through Open WebUI config
state, and the DB remains the practical authority for provider mode even though
the live service sets `ENABLE_PERSISTENT_CONFIG=False`. Keep the active LiteLLM
connection on the standard Chat Completions path.

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

## LiteLLM connection checks
Verify the active Open WebUI LiteLLM/OpenAI connection is not pinned to
Responses mode:

```bash
python3 - <<'PY'
import json, sqlite3, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
req = urllib.request.Request(
    'http://127.0.0.1:3000/openai/config',
    headers={'Authorization': f'Bearer {api_key}'},
)
with urllib.request.urlopen(req, timeout=20) as resp:
    print(resp.read().decode())
PY
```

Expected:
- `OPENAI_API_BASE_URLS` still points at `http://127.0.0.1:4000/v1`
- `OPENAI_API_CONFIGS` is `{}` or has no `api_type=responses` entry

If the DB still shows `api_type=responses`, clear it before restart:

```bash
python3 - <<'PY'
import json, sqlite3
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
rowid, raw = cur.execute('select id, data from config limit 1').fetchone()
data = json.loads(raw)
data.setdefault('openai', {})['api_configs'] = {}
cur.execute('update config set data=? where id=?', (json.dumps(data), rowid))
conn.commit()
print('cleared openai.api_configs for row', rowid)
PY
sudo systemctl restart open-webui.service
```

## Open Terminal registrations
Open WebUI currently uses:
- native terminal server: `http://127.0.0.1:8010`
- read-only MCP tool server: `http://127.0.0.1:8011/mcp`
- Keep native tool calling off for `chatgpt-5` in Open WebUI.
- `chatgpt-5` is now text-only in Open WebUI.
- Open WebUI strips `terminal_id`, `tool_ids`, direct tool servers,
  caller-supplied OpenAI `tools`, and `function_calling` for `chatgpt-5` before
  request execution.
- The restart hotfix path must also prevent any later fallback that would
  silently reattach `open-terminal` for this lane.
- Do not use this lane for repo review, terminal actions, MCP, or tool calling
  in the UI.
- Use the regular local models for tool-using workflows in Open WebUI.

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

## `chatgpt-5` text-only canary
Use a direct text-only probe and verify:
- the reply completes with non-empty assistant content
- no tool/source entries are attached
- terminal/tool-related request fields are ignored even when the caller sends
  them explicitly
- `journalctl -u litellm-orch.service` shows a normal `POST /v1/chat/completions`
  success for `chatgpt-5`

Reference canary:

```bash
python3 - <<'PY'
import json, sqlite3, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
payload = {
    "model": "chatgpt-5",
    "stream": False,
    "terminal_id": "open-terminal",
    "tool_ids": ["server:mcp:open-terminal-mcp-ro"],
    "metadata": {
        "tool_servers": [{"id": "direct", "specs": []}],
        "params": {"function_calling": "native"},
    },
    "tools": [{"type": "function", "function": {"name": "noop", "parameters": {"type": "object"}}}],
    "messages": [{"role": "user", "content": "Reply with exactly text-only-ok"}],
}
req = urllib.request.Request(
    'http://127.0.0.1:3000/api/chat/completions',
    data=json.dumps(payload).encode(),
    headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    },
)
with urllib.request.urlopen(req, timeout=60) as resp:
    body = json.loads(resp.read().decode())
    print(json.dumps(body, indent=2))
PY
```

Success criteria:
- assistant content is non-empty
- no tool/source path is attached for this lane
- the lane does not enter OWUI tool flow at all
- `journalctl -u open-webui.service` does not show terminal access tied to this
  request after restart

## End-to-end voice canary
- restart Open WebUI
- open the UI and complete one voice turn
- confirm LiteLLM logs show `voice-stt-canary` and `voice-tts-canary`
- confirm no direct Orin URL is configured in Open WebUI audio settings
