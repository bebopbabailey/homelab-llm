# Runbook: Open WebUI

## Start/stop
```bash
sudo systemctl start open-webui.service
sudo systemctl stop open-webui.service
sudo systemctl restart open-webui.service
sudo systemctl restart open-webui-elasticsearch-bridge.service
```

## Logs
```bash
journalctl -u open-webui.service -f
```

## Config authority
Audio env still comes from `/etc/open-webui/env`.
Knowledge backend wiring now comes from systemd drop-ins, not ad-hoc UI edits.
Terminal/tool server registrations currently come from the Open WebUI config
API and persist in Open WebUI state.
The LiteLLM/OpenAI provider connection also persists through Open WebUI config
state, and the DB remains the practical authority for provider mode even though
the live service sets `ENABLE_PERSISTENT_CONFIG=False`. Keep the active LiteLLM
connection on the standard Chat Completions path.

The current global web-search query-generation prompt is owned by the systemd
drop-in:
- `/etc/systemd/system/open-webui.service.d/25-querygen-prompt-policy.conf`

## Web search hardening
The supported Mini path stays:
- `WEB_SEARCH_ENGINE=searxng`
- `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`
- `WEB_LOADER_ENGINE=safe_web`

On restart, `scripts/openwebui_querygen_hotfix.py` patches the installed Open
WebUI runtime in place to:
- keep the raw user query as the first search query
- normalize generated rewrites so month/year prefixes do not dominate the query
- add a narrow pre-fetch result hygiene pass that drops obvious zero-overlap
  junk before page loading/embedding
- keep at most two weak or low-confidence fallback results when the strict
  overlap filter would otherwise leave the search with nothing usable

The current prompt override also tells query generation to:
- keep queries topic-first and date-last
- never start with a standalone month name
- avoid generic community/forum/discussion/sentiment-only rewrites unless the
  concrete topic is included

Check the live prompt body here:
```bash
sudo sed -n '1,120p' /etc/systemd/system/open-webui.service.d/25-querygen-prompt-policy.conf
python3 - <<'PY'
import json, sqlite3, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
req = urllib.request.Request('http://127.0.0.1:3000/api/v1/tasks/config', headers={'Authorization': f'Bearer {api_key}'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())
print(data['QUERY_GENERATION_PROMPT_TEMPLATE'])
PY
```

Use this to verify the patch landed:
```bash
python3 - <<'PY'
from pathlib import Path

targets = [
    Path('/home/christopherbailey/homelab-llm/layer-interface/open-webui/.venv/lib/python3.12/site-packages/open_webui/utils/middleware.py'),
    Path('/home/christopherbailey/homelab-llm/layer-interface/open-webui/.venv/lib/python3.12/site-packages/open_webui/routers/retrieval.py'),
]
markers = [
    'querygen-hardening: avoid poisoned queries fallback; normalize generated search queries',
    'web-search-result-hygiene: drop low-overlap junk before fetch; keep bounded low-confidence fallback',
]
for target, marker in zip(targets, markers):
    text = target.read_text(encoding='utf-8')
    print(target.name, marker in text)
PY
```

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

## Knowledge backend install
Install the bridge and reconciliation drop-ins from the repo:

```bash
sudo install -D -m 644 services/open-webui/systemd/open-webui-elasticsearch-bridge.service \
  /etc/systemd/system/open-webui-elasticsearch-bridge.service
sudo install -D -m 644 services/open-webui/systemd/80-knowledge-backend-sync.conf \
  /etc/systemd/system/open-webui.service.d/80-knowledge-backend-sync.conf
sudo install -D -m 644 services/open-webui/systemd/81-knowledge-bridge-dependency.conf \
  /etc/systemd/system/open-webui.service.d/81-knowledge-bridge-dependency.conf
sudo systemctl daemon-reload
sudo systemctl enable --now open-webui-elasticsearch-bridge.service
sudo systemctl restart open-webui.service
```

Canonical runtime values:
- `VECTOR_DB=elasticsearch`
- `ELASTICSEARCH_URL=http://127.0.0.1:19200`
- `ELASTICSEARCH_INDEX_PREFIX=open_webui_collections`
- `RAG_EMBEDDING_ENGINE=openai`
- `RAG_OPENAI_API_BASE_URL=http://192.168.1.72:55440/v1`
- `RAG_EMBEDDING_MODEL=studio-nomic-embed-text-v1.5`
- `RAG_EMBEDDING_PREFIX_FIELD_NAME=prefix`
- `RAG_EMBEDDING_QUERY_PREFIX=search_query:`
- `RAG_EMBEDDING_CONTENT_PREFIX=search_document:`
- `ENABLE_RAG_HYBRID_SEARCH=true`
- `ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS=true`
- `RAG_FULL_CONTEXT=false`
- `RAG_TOP_K=5`
- `RAG_RELEVANCE_THRESHOLD=0.0`
- `CHUNK_SIZE=1000`
- `CHUNK_OVERLAP=100`

## Knowledge backend verification
Bridge health and bind:

```bash
systemctl is-active open-webui-elasticsearch-bridge.service
ss -ltn '( sport = :19200 )'
curl -fsS http://127.0.0.1:19200/_cluster/health | jq .
```

Reconciliation helper:

```bash
python3 services/open-webui/scripts/openwebui_knowledge_sync.py --check-only
```

Admin API verification:

```bash
python3 - <<'PY'
import json, sqlite3, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
headers = {'Authorization': f'Bearer {api_key}'}
for path in ['api/v1/retrieval/embedding', 'api/v1/retrieval/config']:
    req = urllib.request.Request(f'http://127.0.0.1:3000/{path}', headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    print(path, json.dumps(data, indent=2))
PY
```

Expected:
- embedding engine/model point at `vector-db` + `studio-nomic-embed-text-v1.5`
- `TOP_K=5`
- hybrid search enabled
- `CHUNK_SIZE=1000`
- `CHUNK_OVERLAP=100`

## Everyday Knowledge flow
1. Create a collection in `Workspace -> Knowledge`.
2. Upload manuals, study PDFs, or AI/IT docs.
3. Open `deep` or `fast`.
4. Attach the collection or reference it with `#`.
5. Use Focused Retrieval by default.

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
