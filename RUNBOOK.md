# Runbook: LiteLLM (litellm-orch)

## Start/stop
```bash
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
```

## Port policy
- Studio `8100-8119`: team lanes managed by `mlxctl`.
- Studio `8120-8139`: experimental lanes (no `mlxctl` requirement).
- Active canonical Mini -> Studio MLX transport uses the Studio LAN IP
  `192.168.1.72` for `8100/8101/8102`.

## Direct Studio MLX reachability (Mini)
```bash
for p in 8100 8101 8102; do
  curl -fsS "http://192.168.1.72:${p}/v1/models" | jq .
done
```

## Experimental alias checks
```bash
rg -n "metal-test-fast|metal-test-main|metal-test-deep|metal-test-gptoss20b-enforce" \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
```

## GPT-OSS 20B enforced lane checks
`metal-test-gptoss20b-enforce` is a Responses-only experimental lane for GPT-OSS
20B. It normalizes `stream=false` and `temperature=0.0`, rejects
chat/completions calls, and must not rewrite tool schemas or response content.

Durable observability source of truth for the kept lane:
- `journalctl -u litellm-orch.service | rg 'responses_contract_guardrail|policy_(decision|result|summary)'`

Convenience trace for ad hoc debugging during experiments:
- `/tmp/litellm_responses_contract_guardrail.jsonl`

Quick checks:
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

journalctl -u litellm-orch.service -n 100 --no-pager | \
  rg 'responses_contract_guardrail|policy_(decision|result|summary)'

curl -sS -o /tmp/gptoss20b-enforce.reject.json -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"metal-test-gptoss20b-enforce","messages":[{"role":"user","content":"Reply with exactly: reject-ok"}],"stream":true,"max_tokens":32}'

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"metal-test-gptoss20b-enforce","input":"Reply with exactly: lane-ok","stream":true}' | jq .
```

## Harmony normalization checks (GPT lanes)
```bash
rg -n "modify_params|target_models|coerce_stream_false" \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml
```

Expected:
- Harmony guardrails still target GPT lanes.
- No web-search-specific pre-call or post-call guardrails remain.

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

curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  "http://127.0.0.1:4000/v1/model/info" | jq '.data[] | select(.model_name=="code-reasoning")'

rg -n "websearch-schema|websearch_schema_guardrail|web_answer|fast-research" \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/SERVICE_SPEC.md \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/docs/openwebui.md
```

Expected:
- `code-reasoning`, `fast`, `main`, `deep`, and `boost*` aliases appear in `/v1/models`.
- `voice-stt-canary`, `voice-tts-canary`, `voice-stt`, and `voice-tts` appear in `/v1/models`.
- `fast-research` is absent.
- No LiteLLM config references remain for `websearch-schema`, `websearch_schema_guardrail`, or `web_answer`.
- Current resilience baseline keeps `fast -> main`.
- `code-reasoning` model info reports explicit capability metadata for OpenHands discovery.

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
- LiteLLM returns the structured tool call unchanged from the `8101` backend

## OpenHands worker policy validation
Verify the live capability path first:
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  "http://127.0.0.1:4000/v1/model/info" | jq '.data[] | select(.model_name=="code-reasoning")'
```

Verify the worker key can only use the stable coding alias and cannot reach MCP:
```bash
export OPENHANDS_WORKER_KEY='<worker-key>'
export OPENHANDS_LITELLM_BASE_URL='http://192.168.1.71:4000/v1'

curl -fsS -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  "${OPENHANDS_LITELLM_BASE_URL}/models" | jq .

curl -fsS -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  "${OPENHANDS_LITELLM_BASE_URL}/model/info" | jq .

curl -fsS "${OPENHANDS_LITELLM_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"code-reasoning","messages":[{"role":"user","content":"Reply with exactly: code-reasoning-ok"}],"stream":false,"max_tokens":32}' | jq .

curl -sS -o /dev/null -w "%{http_code}\n" "${OPENHANDS_LITELLM_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"main","messages":[{"role":"user","content":"Reply with exactly: main-should-fail"}],"stream":false,"max_tokens":32}'

curl -sS -o /dev/null -w "%{http_code}\n" "${OPENHANDS_LITELLM_BASE_URL}/mcp/tools" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}"

curl -sS -o /dev/null -w "%{http_code}\n" "${OPENHANDS_LITELLM_BASE_URL}/model/info" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}"

curl -sS -o /dev/null -w "%{http_code}\n" "${OPENHANDS_LITELLM_BASE_URL}/responses" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"code-reasoning","input":"route-check"}'
```

Expected:
- `/v1/models` returns only `code-reasoning`.
- `/model/info` returns exactly one `code-reasoning` record for the worker key.
- `code-reasoning` succeeds.
- direct `main` access is rejected.
- MCP tool listing is rejected for the worker key.
- `/responses` is rejected by route allowlisting.
- If `code-reasoning` returns upstream `404` for missing served model identity,
  triage Studio lane drift first with `mlxctl status --json` and
  `ssh studio "curl -fsS http://127.0.0.1:8101/v1/models | jq ."`.

## Readiness callback check
```bash
curl -fsS http://127.0.0.1:4000/health/readiness | jq -r '.success_callbacks[]'
```

Expected:
- `PromptGuardrail`, `HarmonyGuardrail`, and `TranscribeGuardrail` remain.
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
