# Runbook: LiteLLM (litellm-orch)

## Start/stop
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch
uv sync --frozen

sudo systemctl start litellm-orch.service
sudo systemctl stop litellm-orch.service
sudo systemctl restart litellm-orch.service
```

## Logs
```bash
journalctl -u litellm-orch.service -f
```

## Health
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://127.0.0.1:4000/health
curl http://127.0.0.1:4000/health/readiness
curl http://127.0.0.1:4000/health/liveliness
curl http://127.0.0.1:4000/metrics/
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://127.0.0.1:4000/v1/mcp/tools | jq .
```

## Port policy
- Studio `8100-8119`: team lanes managed by `mlxctl`.
- Studio `8120-8139`: experimental lanes (no `mlxctl` requirement).
- Active canonical Mini -> Studio MLX transport uses the Studio LAN IP
  `192.168.1.72` for `8101` (public `main`) and `8126` (public `fast` + `deep`).

## Direct Studio backend reachability (Mini)
```bash
for p in 8101 8126; do
  curl -fsS "http://192.168.1.72:${p}/v1/models" | jq .
done
```

## GPT request-default checks
```bash
rg -n "gpt-request-defaults|target_models|reasoning_effort" \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml
```

Expected:
- `gpt-request-defaults` targets `deep`, `fast`, and `code-reasoning`.
- `gpt-request-defaults` does not target `chatgpt-5` or `chatgpt-5-thinking`.
- No web-search-specific pre-call or post-call guardrails remain.
- No GPT-lane post-call formatting guardrail remains active.

## GPT streaming checks (pass-through)
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -N -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"fast","stream":true,"messages":[{"role":"user","content":"Reply with exactly: stream-ok"}],"max_tokens":32}'

curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"fast","stream":false,"messages":[{"role":"user","content":"Reply with exactly: nonstream-ok"}],"max_tokens":32}' | jq .
```

## GPT acceptance harness (public lanes)
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

uv run python /home/christopherbailey/homelab-llm/layer-inference/llama-cpp-server/scripts/run_gpt_oss_acceptance.py \
  --base-url http://127.0.0.1:4000/v1 \
  --model fast \
  --api-key "$LITELLM_MASTER_KEY" \
  --profile fast
```

Current GPT public-lane posture:
- Chat Completions-first
- `/v1/responses` remains advisory
- `fast` is now canonical on shared `8126`
- `deep` is now live on shared `8126` under the usable-success contract
- GPT formatting/tool-call parsing is upstream-owned for `main`, `fast`, and
  `deep`; LiteLLM only injects omitted `reasoning_effort=low` for GPT `llmster`
  lanes

Temporary GPT canary alias:
- no temporary GPT canary alias is active in the current gateway contract

## Fallback validation
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"fast","messages":[{"role":"user","content":"Reply with exactly one short sentence."}],"stream":false,"max_tokens":32,"mock_testing_fallbacks":true}' | jq .
```
Expected:
- request succeeds
- LiteLLM logs show `fast` falling back to `main`

## Active alias checks
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | sort

rg -n "websearch-schema|websearch_schema_guardrail|web_answer|fast-research" \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/SERVICE_SPEC.md \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/docs/openwebui.md
```

Expected:
- `/v1/models` includes `main`, `deep`, `fast`, and `code-reasoning`.
- `/v1/models` includes `chatgpt-5` and `chatgpt-5-thinking`.
- `/v1/models` includes `task-transcribe` and `task-transcribe-vivid`.
- `/v1/models` includes `task-json`.
- `fast-research` is absent.
- No LiteLLM config references remain for `websearch-schema`, `websearch_schema_guardrail`, or `web_answer`.
- Current resilience baseline keeps `fast -> main`.
- `helper`, `boost*`, shadow aliases, and `metal-test-*` are absent from the active LLM alias surface.

## ChatGPT alias smoke checks
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"chatgpt-5","messages":[{"role":"user","content":"Reply with exactly: chatgpt-5-ok"}],"stream":false}' | jq .

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"chatgpt-5-thinking","messages":[{"role":"user","content":"Reply with exactly: chatgpt-5-thinking-ok"}],"stream":false}' | jq .
```

Expected:
- the first call may trigger LiteLLM's ChatGPT device-code auth flow
- `journalctl -u litellm-orch.service -f` shows the verification URL and device code when auth is required
- successful follow-up calls return the expected exact text
- no base URL change is required in Open WebUI

Historical cutover order:
- raw `deep`
- direct `llmster` `deep`
- temporary canary alias (now retired)
- only then canonical public `deep`

Current public `deep` cutover result:
- plain chat `5/5`
- structured simple `5/5`
- structured nested `5/5`
- auto noop `10/10`
- auto arg-bearing `10/10`
- required arg-bearing `9/10`
- named forced-tool choice unsupported on current backend path

## Speech canary checks
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/audio/speech \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"voice-tts-canary","input":"LiteLLM speech canary.","voice":"alloy","response_format":"wav","speed":1.0}' \
  --output /tmp/litellm-voice-canary.wav

curl -fsS http://127.0.0.1:4000/v1/audio/transcriptions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -F 'file=@/tmp/litellm-voice-canary.wav' \
  -F 'model=voice-stt-canary'
```

Expected:
- both calls succeed through LiteLLM
- LiteLLM logs show `voice-tts-canary` and `voice-stt-canary`
- the Orin `voice-gateway` LAN `api_base` is used directly
- `task-transcribe*` remains untouched

## Transcript alias checks
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-transcribe","stream":false,"max_tokens":128,"messages":[{"role":"user","content":"um i i think this should probably work maybe yes"}]}' | jq -r '.choices[0].message.content'

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-transcribe-vivid","stream":false,"max_tokens":128,"prompt_variables":{"audience":"internal notes","tone":"lightly polished"},"messages":[{"role":"user","content":"uh okay this is kind of sudden but it matters a lot actually"}]}' | jq -r '.choices[0].message.content'
```

Expected:
- both aliases succeed through `POST /v1/chat/completions`
- outputs are plain cleaned transcript text with no wrapper label or commentary
- `task-transcribe-vivid` accepts optional `audience` and `tone` prompt variables

## Task JSON alias check
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-json","stream":false,"messages":[{"role":"user","content":"call mom tomorrow at 3, buy milk, and pick up paper towels"}]}' \
  | jq '.choices[0].message.content | fromjson'
```

Expected:
- the call succeeds through `POST /v1/chat/completions`
- `message.content` parses as JSON
- the parsed object has exact top-level keys `todo`, `grocery`, `purchase`, and `other`
- `other` contains only `items` and `attributes`

## Main tool-calling validation
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

python3 - <<'PY'
import json, os, urllib.request
payload={
  'model':'main',
  'messages':[{'role':'user','content':'Use the noop tool once, then stop.'}],
  'tools':[{'type':'function','function':{'name':'noop','description':'noop','parameters':{'type':'object','properties':{}}}}],
  'tool_choice':'auto',
  'stream':False,
  'max_tokens':128
}
req=urllib.request.Request(
  'http://127.0.0.1:4000/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Authorization': f"Bearer {os.environ['LITELLM_MASTER_KEY']}", 'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0]['message'], indent=2))
PY
```

Expected:
- `tool_calls` is present and names `noop`
- `content` does not contain raw `<tool_call>`
- LiteLLM returns the structured tool call natively from the `8101` backend

Argument-bearing `main` tool-calling validation:
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

python3 - <<'PY'
import json, os, urllib.request
payload={
  'model':'main',
  'messages':[{'role':'user','content':'Use the noop tool exactly once with a short JSON object argument.'}],
  'tools':[{'type':'function','function':{'name':'noop','description':'noop','parameters':{'type':'object','properties':{'value':{'type':'string'}},'required':['value'],'additionalProperties':False}}}],
  'tool_choice':'auto',
  'stream':False,
  'max_tokens':128
}
req=urllib.request.Request(
  'http://127.0.0.1:4000/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Authorization': f"Bearer {os.environ['LITELLM_MASTER_KEY']}", 'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0]['message'], indent=2))
PY
```

Expected:
- `tool_calls` is present and names `noop`
- parsed `tool_calls[0].function.arguments` contains a JSON object with key `value`
- `content` does not contain raw `<tool_call>`
- this is produced natively by the locked `8101` backend render

Structured-output reality check:
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

python3 - <<'PY'
import json, os, urllib.request
payload={
  'model':'main',
  'messages':[{'role':'user','content':'Return JSON matching the schema.'}],
  'response_format':{
    'type':'json_schema',
    'json_schema':{
      'name':'status_payload',
      'schema':{
        'type':'object',
        'properties':{'status':{'type':'string'}},
        'required':['status'],
        'additionalProperties':False
      },
      'strict':True
    }
  },
  'max_tokens':64,
  'temperature':0
}
req=urllib.request.Request(
  'http://127.0.0.1:4000/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Authorization': f"Bearer {os.environ['LITELLM_MASTER_KEY']}", 'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0]['message'], indent=2))
PY
```

Current expected result:
- this exact `response_format.json_schema` shape is still failing on the current
  Qwen `main` path and returns a backend-produced error payload
- do not treat `main` structured outputs as fully hardened until that exact
  request shape is repaired
  post-call success hook if the backend returns the strict recoverable raw form

## OpenHands worker contract
OpenHands Phase B is gated by one reserved internal worker alias only:
- alias: `code-reasoning`
- backend target: `deep`
- contract shape: Chat Completions-first ordinary tool use
- unsupported/out of contract:
  - named/object-form forced-tool choice
  - strict structured-output/schema guarantees
  - MCP access
  - `/v1/responses`

Worker-key verification:
```bash
OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)

curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" | jq .

curl -fsS http://127.0.0.1:4000/v1/model/info \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" | jq .

curl -fsS http://127.0.0.1:4000/model/info \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" | jq .

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"code-reasoning","messages":[{"role":"user","content":"Reply with exactly: code-reasoning-ok"}],"stream":false,"max_tokens":32}' | jq .

curl -sS -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/mcp/tools \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}"

curl -sS -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"code-reasoning","input":"hello"}'
```

Expected:
- `/v1/models` returns `code-reasoning`
- `/v1/model/info` and `/model/info` both succeed for the worker key
- `/v1/chat/completions` succeeds for `code-reasoning`
- `/v1/mcp/tools` returns `403`
- `/v1/responses` returns `403`

Unsupported-feature probes:
```bash
OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"code-reasoning",
    "messages":[{"role":"user","content":"Call noop once with {\"value\":\"x\"}."}],
    "tools":[{"type":"function","function":{"name":"noop","description":"noop","parameters":{"type":"object","properties":{"value":{"type":"string"}},"required":["value"],"additionalProperties":false}}}],
    "tool_choice":{"type":"function","function":{"name":"noop"}},
    "stream":false,
    "max_tokens":128
  }' | jq .

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"code-reasoning",
    "messages":[{"role":"user","content":"Return JSON matching the schema exactly."}],
    "response_format":{
      "type":"json_schema",
      "json_schema":{
        "name":"status_payload",
        "schema":{"type":"object","properties":{"status":{"type":"string"}},"required":["status"],"additionalProperties":false},
        "strict":true
      }
    },
    "stream":false,
    "max_tokens":128,
    "temperature":0
  }' | jq .
```

Expected:
- named/object-form forced tool choice is rejected or backend-visible unsupported
- strict structured-output/schema guarantee is rejected, ignored, or otherwise
  not boring enough to advertise for `code-reasoning`

## Readiness callback check
```bash
curl -fsS http://127.0.0.1:4000/health/readiness | jq -r '.success_callbacks[]'

journalctl -u litellm-orch.service -n 200 --no-pager | rg 'GPTRequestDefaults|TranscribeGuardrail'
```

Expected:
- `/health/readiness` currently reports `sync_deployment_callback_on_success`
  and `PrometheusLogger`.
- journald shows `GPTRequestDefaults` and `TranscribeGuardrail` loading at startup.
- `WebsearchSchemaGuardrail` is absent.

## Search tool checks
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
curl -fsS http://127.0.0.1:4000/v1/search/searxng-search \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"openvino llm","max_results":3}' | jq .
```

Note:
- `/v1/search/searxng-search` remains for direct callers and MCP tools.
- Open WebUI web search is configured in Open WebUI itself and does not depend on LiteLLM prompt-shape or schema middleware.
