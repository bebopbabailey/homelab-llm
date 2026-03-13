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

## Config Authority Warning
`ENABLE_PERSISTENT_CONFIG=False` makes systemd env/drop-ins authoritative.
Admin UI edits to web-search settings are session-only and lost on restart.

## TTS Proof Path
- Current TTS proof target is Voice Gateway on the Orin, not a second LiteLLM path.
- Keep the current global LiteLLM settings in `/etc/open-webui/env` unchanged.
- Do not repoint `OPENAI_API_BASE_URL` or `OPENAI_API_KEY` for TTS.
- Current proof reachability path on the Mini:
```bash
ssh -fN -o ExitOnForwardFailure=yes -L 127.0.0.1:18081:127.0.0.1:18080 orin
```
- Dedicated TTS config fields exposed by the installed Open WebUI build:
  - `AUDIO_TTS_ENGINE`
  - `AUDIO_TTS_OPENAI_API_BASE_URL`
  - `AUDIO_TTS_OPENAI_API_KEY`
  - `AUDIO_TTS_MODEL`
  - `AUDIO_TTS_VOICE`
  - `AUDIO_TTS_OPENAI_PARAMS`
  - `AUDIO_TTS_SPLIT_ON`
- Current proof target values:
  - `AUDIO_TTS_ENGINE=openai`
  - `AUDIO_TTS_OPENAI_API_BASE_URL=http://127.0.0.1:18081/v1`
  - `AUDIO_TTS_OPENAI_API_KEY=voice-gateway-local-dev`
  - `AUDIO_TTS_MODEL=xtts-v2`
  - `AUDIO_TTS_VOICE=default`
  - `AUDIO_TTS_OPENAI_PARAMS={}`
- TTS-only in this phase. STT remains out of scope.

Verify no dedicated TTS env is set yet:
```bash
rg -n '^AUDIO_TTS_' /etc/open-webui/env || true
```

Verify the forwarded backend:
```bash
curl -fsS http://127.0.0.1:18081/health
curl -m 180 -fsS http://127.0.0.1:18081/health/readiness
curl -m 180 -fsS http://127.0.0.1:18081/v1/speakers
curl -fsS \
  -H "Content-Type: application/json" \
  -d '{"model":"xtts-v2","input":"Phase one voice gateway check.","voice":"default","response_format":"wav","language":"en"}' \
  http://127.0.0.1:18081/v1/audio/speech \
  --output /tmp/openwebui-tts-smoke.wav
file /tmp/openwebui-tts-smoke.wav
```

## Querygen hotfix verification
```bash
sudo systemctl cat open-webui.service --no-pager | rg -n "50-querygen-hotfix|ExecStartPre"
rg -n "querygen-hardening: avoid poisoned queries fallback" \
  /home/christopherbailey/homelab-llm/layer-interface/open-webui/.venv/lib/python3.12/site-packages/open_webui/utils/middleware.py
```

## Helper-task lane isolation verification
```bash
sudo systemctl cat open-webui.service --no-pager | rg -n "60-task-model-isolation|TASK_MODEL|TASK_MODEL_EXTERNAL"
systemctl show -p Environment open-webui.service | rg -n "TASK_MODEL=|TASK_MODEL_EXTERNAL="
```

## Web search configuration verification
```bash
systemctl show -p Environment open-webui.service --no-pager | rg -n \
  'ENABLE_PERSISTENT_CONFIG=False|ENABLE_WEB_SEARCH=True|WEB_SEARCH_ENGINE=searxng|SEARXNG_QUERY_URL=http://127.0.0.1:8888/search\\?q=<query>&format=json|WEB_SEARCH_RESULT_COUNT=6|WEB_SEARCH_CONCURRENT_REQUESTS=1|WEB_LOADER_ENGINE=safe_web|WEB_LOADER_TIMEOUT=15|WEB_LOADER_CONCURRENT_REQUESTS=2|WEB_FETCH_FILTER_LIST=|WEB_SEARCH_DOMAIN_FILTER_LIST='

systemctl show -p Environment open-webui.service --no-pager | rg -n \
  'EXTERNAL_WEB_LOADER_URL|SEARXNG_QUERY_URL=http://127.0.0.1:8899/search\\?q=<query>|WEB_LOADER_ENGINE=external'
```

## SearXNG backend smoke test
```bash
curl -fsS "http://127.0.0.1:8888/search?q=evidence-based+wok+tips&format=json" \
  | jq '{count:(.results|length), first:(.results[0] // {}) | {title, url}}'
```

## Open WebUI end-to-end web search smoke
```bash
export OWUI_API_KEY='<open-webui-api-key>'
curl -N -fsS http://127.0.0.1:3000/api/chat/completions \
  -H "Authorization: Bearer ${OWUI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"fast",
    "stream":true,
    "messages":[{"role":"user","content":"Search the web for two recent Open WebUI and SearXNG references and summarize them in two bullets."}],
    "features":{"web_search":true}
  }'
```

Then confirm:
```bash
rg -n '"type": "web_search"|"type":"web_search"|"sources": \\[' /tmp/owui-websearch-smoke.ndjson
rg -n '"content"|"delta"' /tmp/owui-websearch-smoke.ndjson | tail -n 40
```

Expected:
- the stream includes a `sources` event with `type: "web_search"`
- assistant content deltas are present and the stream finishes normally
- no `websearch-orch` env references remain on the service

## Health
```bash
curl http://127.0.0.1:3000/health
```
