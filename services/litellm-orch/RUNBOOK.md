# Runbook: LiteLLM (litellm-orch)

## Start/stop
```bash
cd /home/christopherbailey/homelab-llm/services/litellm-orch
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
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://127.0.0.1:4000/health
curl http://127.0.0.1:4000/health/readiness
curl http://127.0.0.1:4000/health/liveliness
curl http://127.0.0.1:4000/metrics/
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://127.0.0.1:4000/v1/mcp/tools | jq .
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://127.0.0.1:4000/v1/mcp/server | jq .
```

DB-backed auth note:
- `DATABASE_URL` must be present in the service environment for LiteLLM-owned
  teams, groups, service accounts, and `/key/generate`.
- For this deployment, readiness is not acceptable when
  `.db == "Not connected"`, even if `/health/readiness` still returns `200`.
- If local agents or worker keys return `{"type":"no_db_connection"}`, check
  `/health/readiness` first and restore `DATABASE_URL` before deeper route or
  alias triage.

## Prisma schema repair (Mini)
Use this only when LiteLLM is healthy enough to start but runtime features such
as `/key/generate` or `/v1/mcp/*` fail with Prisma client/schema drift.

Symptoms seen on the broken Mini runtime:
- `/key/generate` returned `500`
- MCP routes raised missing-model errors such as `litellm_tooltable` or
  `litellm_configoverrides`
- journald showed `AttributeError` against Prisma client attributes that exist
  in the shipped LiteLLM schema but not in the generated client / DB

Supported repair path used on Mini:
```bash
cd /home/christopherbailey/homelab-llm/services/litellm-orch
set -a
source config/env.local >/dev/null 2>&1

uv run litellm --config config/router.yaml \
  --skip_server_startup \
  --enforce_prisma_migration_check \
  --use_prisma_db_push

uv run prisma py generate \
  --schema .venv/lib/python3.12/site-packages/litellm_proxy_extras/schema.prisma

sudo systemctl restart litellm-orch.service
journalctl -u litellm-orch.service -n 120 --no-pager
```

Mini-specific ownership repair that was required before `db push` could finish:
```bash
sudo -u postgres psql -d litellm -v ON_ERROR_STOP=1 <<'SQL'
REASSIGN OWNED BY litellm TO bebopbabailey;
ALTER DATABASE litellm OWNER TO bebopbabailey;
SQL
```

Expected post-repair checks:
- `curl http://127.0.0.1:4000/health/readiness` returns healthy and does not
  report `db: "Not connected"`
- `POST /key/generate` succeeds
- `GET /v1/models` succeeds
- `GET /v1/mcp/server` succeeds

## Port policy
- Studio `8100-8119`: team lanes managed by `mlxctl`.
- Studio `8120-8139`: experimental lanes (no `mlxctl` requirement).
- Active canonical Mini -> Studio MLX transport uses the Studio LAN IP
  `192.168.1.72` for `8126` (public `fast` + `deep`).

## Direct Studio backend reachability (Mini)
```bash
for p in 8126; do
  curl -fsS "http://192.168.1.72:${p}/v1/models" | jq .
done
```

## GPT request-default checks
```bash
rg -n "gpt-request-defaults|target_models|reasoning_effort" \
  /home/christopherbailey/homelab-llm/services/litellm-orch/config/router.yaml
```

Expected:
- `gpt-request-defaults` targets `deep`, `fast`, and `code-reasoning`.
- No web-search-specific pre-call or post-call guardrails remain.
- No GPT-lane post-call formatting guardrail remains active.

## GPT Chat Completions compatibility checks
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

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
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

uv run python /home/christopherbailey/homelab-llm/services/llama-cpp-server/scripts/run_gpt_oss_acceptance.py \
  --base-url http://127.0.0.1:4000/v1 \
  --model fast \
  --api-key "$LITELLM_MASTER_KEY" \
  --profile fast
```

Current GPT public-lane posture:
- Responses-first for `fast`, `deep`, `task-transcribe`, `task-transcribe-vivid`, `task-json`, and `task-youtube-summary`
- `/v1/chat/completions` remains temporary compatibility only for those public GPT-OSS aliases
- `fast` is now canonical on shared `8126`
- `deep` is now live on shared `8126` under the usable-success contract
- GPT formatting/tool-call parsing is upstream-owned for `fast` and `deep`;
  LiteLLM only injects omitted reasoning defaults and task-alias shaping where direct `8126` still requires it

## GPT Responses checks (public lanes)
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"fast","input":"Reply with exactly: responses-fast-ok","max_output_tokens":128}' | jq .

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"deep","input":"Reply with exactly: responses-deep-ok","max_output_tokens":128}' | jq .
```
Expected:
- both responses complete with a final assistant message in `output`
- requests are normalized to `temperature=0.0`
- omitted reasoning defaults are injected upstream for GPT-OSS lanes
- direct-style clients should treat `output` as the canonical text surface for
  raw `fast` / `deep`; `output_text` is not guaranteed upstream

Temporary GPT canary alias:
- no temporary GPT canary alias is active in the current gateway contract

## Fallback validation
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"fast","messages":[{"role":"user","content":"Reply with exactly one short sentence."}],"stream":false,"max_tokens":32,"mock_testing_fallbacks":true}' | jq .
```
Expected:
- request succeeds
- LiteLLM logs show `fast` falling back to `deep`

## Active alias checks
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | sort

rg -n "websearch-schema|websearch_schema_guardrail|web_answer|fast-research" \
  /home/christopherbailey/homelab-llm/services/litellm-orch/config/router.yaml \
  /home/christopherbailey/homelab-llm/services/litellm-orch/SERVICE_SPEC.md \
  /home/christopherbailey/homelab-llm/services/litellm-orch/docs/openwebui.md
```

Expected:
- `/v1/models` includes `deep`, `fast`, and `code-reasoning`.
- `/v1/models` includes `task-transcribe` and `task-transcribe-vivid`.
- `/v1/models` includes `task-json`.
- `/v1/models` includes `task-youtube-summary`.
- `fast-research` is absent.
- No LiteLLM config references remain for `websearch-schema`, `websearch_schema_guardrail`, or `web_answer`.
- Current resilience baseline keeps `fast -> deep`.
- `helper`, `boost*`, shadow aliases, and `metal-test-*` are absent from the active LLM alias surface.

Task-alias Responses smokes:
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-transcribe","input":[{"role":"user","content":"um i i think this should probably work maybe yes"}],"max_output_tokens":384}' | jq .

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-transcribe-vivid","input":[{"role":"user","content":"uh okay this is kind of sudden but it matters a lot actually"}],"max_output_tokens":256}' | jq .

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-json","input":[{"role":"user","content":"call mom tomorrow, buy milk, pick up paper towels"}],"max_output_tokens":512}' | jq .

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-youtube-summary","input":[{"role":"user","content":"https://youtu.be/dQw4w9WgXcQ focus on the main claims and examples"}],"max_output_tokens":2048}' | jq .
```
Expected:
- `task-transcribe` returns cleaned transcript text in the final Responses `message`
- `task-transcribe-vivid` returns cleaned vivid transcript text in the final Responses `message`
- `task-json` returns minified canonical JSON in the final Responses `message`
- `task-youtube-summary` returns markdown with a compact metadata line plus a comprehensive summary in the final Responses `message`
- `task-youtube-summary` depends on the localhost-only `media-fetch-mcp`
  transcript service at `http://127.0.0.1:8012/mcp`; if first-turn transcript
  acquisition fails unexpectedly, check that service before deeper LiteLLM
  routing triage
- long-video follow-ups are expected to resolve through the retrieval service's
  durable `response_id -> document_id` mapping rather than raw provider state
- `config/env.local` must include `MEMORY_API_BEARER_TOKEN=<studio token>` for
  the write-side transcript upserts used by `task-youtube-summary`

Task-alias follow-up/state smoke:
```bash
python3 - <<'PY'
import json, urllib.request

key = None
for line in open("/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local", encoding="utf-8"):
    if line.startswith("LITELLM_MASTER_KEY="):
        key = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

url = "http://127.0.0.1:4000/v1/responses"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
initial = {
    "model": "task-transcribe-vivid",
    "input": [{"role": "user", "content": "uh okay this is kind of sudden but it matters a lot actually"}],
    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
    "max_output_tokens": 256,
}
req = urllib.request.Request(url, data=json.dumps(initial).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=90) as resp:
    first = json.loads(resp.read().decode())

followup = {
    "model": "task-transcribe-vivid",
    "previous_response_id": first["id"],
    "input": [{"role": "user", "content": "Make that a little more formal."}],
    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
    "max_output_tokens": 192,
}
req = urllib.request.Request(url, data=json.dumps(followup).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=90) as resp:
    second = json.loads(resp.read().decode())

print(json.dumps(
    {
        "first_id": first.get("id"),
        "first_output_text": first.get("output_text"),
        "first_cached_tokens": ((first.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens"),
        "second_previous_response_id": second.get("previous_response_id"),
        "second_output_text": second.get("output_text"),
        "second_cached_tokens": ((second.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens"),
    },
    indent=2,
))
PY
```

Expected:
- the initial task response returns a stable `id`
- the follow-up accepts the prior public `id` as input
- the echoed `previous_response_id` may be an internal/raw form and should not
  be compared byte-for-byte against the public `id`
- both responses expose `usage.input_tokens_details.cached_tokens`
- `task-transcribe-vivid` keeps stable `output_text` for Shortcut-style clients

YouTube-summary follow-up/state smoke:
```bash
python3 - <<'PY'
import json, urllib.request

key = None
for line in open("/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local", encoding="utf-8"):
    if line.startswith("LITELLM_MASTER_KEY="):
        key = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

url = "http://127.0.0.1:4000/v1/responses"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
initial = {
    "model": "task-youtube-summary",
    "input": [{"role": "user", "content": "https://youtu.be/dQw4w9WgXcQ focus on the main claims"}],
    "max_output_tokens": 2048,
}
req = urllib.request.Request(url, data=json.dumps(initial).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=180) as resp:
    first = json.loads(resp.read().decode())

followup = {
    "model": "task-youtube-summary",
    "previous_response_id": first["id"],
    "input": [{"role": "user", "content": "What examples did the speaker use?"}],
    "max_output_tokens": 1024,
}
req = urllib.request.Request(url, data=json.dumps(followup).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=120) as resp:
    second = json.loads(resp.read().decode())

print(json.dumps(
    {
        "first_id": first.get("id"),
        "first_prefix": (first.get("output_text") or "")[:120],
        "first_cached_tokens": ((first.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens"),
        "second_previous_response_id": second.get("previous_response_id"),
        "second_prefix": (second.get("output_text") or "")[:120],
    },
    indent=2,
))
PY
```

Expected:
- the initial response starts with the compact metadata line for the video
- the follow-up accepts the prior public `id` as `previous_response_id`
- successful follow-ups no longer depend on upstream placeholder lineage for
  chunked runs; they should resolve through the memory API mapping layer
- short-video runs stay transcript-grounded through the returned response `id`
- chunked long-video runs stay synthesis-grounded because the final synthesis response becomes the public follow-up surface

Experimental ChatGPT/Codex alias checks:
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | sort | rg '^chatgpt-5$'

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"chatgpt-5","messages":[{"role":"user","content":"Reply with exactly: chat-ok"}],"stream":false,"max_tokens":32}' | jq .

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"chatgpt-5","input":[{"role":"user","content":"Reply with exactly: responses-ok"}],"max_output_tokens":32}' | jq .
```

Expected:
- `/v1/models` includes `chatgpt-5`
- Chat Completions succeeds for `chatgpt-5`
- Responses also succeeds for `chatgpt-5`
- the alias is backed by local `ccproxy-api` on `127.0.0.1:4010/codex/v1`
- `gpt-5.3-codex` is the current validated upstream model id for the alias

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

## Llmster MCP tool-call hardening checks
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

/home/christopherbailey/homelab-llm/services/litellm-orch/.venv/bin/python -m unittest discover \
  -s /home/christopherbailey/homelab-llm/services/litellm-orch/tests \
  -p 'test_llmster_toolcall_guardrail.py'

/home/christopherbailey/homelab-llm/services/litellm-orch/.venv/bin/python -m unittest discover \
  -s /home/christopherbailey/homelab-llm/services/litellm-orch/tests \
  -p 'test_router_drop_params.py'

sudo systemctl restart litellm-orch.service

journalctl -u litellm-orch.service -n 120 --no-pager | \
  rg 'llmster_toolcall_guardrail|protocol_tool_call_rewritten|fallback_error'
```

Expected:
- tool-bearing `deep` / `fast` / `code-reasoning` auto-tool requests are forced
  non-streaming before the upstream call
- malformed `to=functions...<|message|>{...}` llmster emissions are either
  rewritten into valid `tool_calls` or converted into a clean retry error
- no raw `<|channel|>` / `to=functions.` protocol text is left in the final
  assistant content for these lanes

## Speech canary checks
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

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
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

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
- outputs do not expose `reasoning`, `reasoning_content`, or `provider_specific_fields`
- `task-transcribe` routes through the `fast` lane and `task-transcribe-vivid` routes through the `deep` lane
- `task-transcribe-vivid` accepts optional `audience` and `tone` prompt variables

## Task JSON alias check
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

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

## Retired main lane
- `main` is not part of the current public LiteLLM contract.
- Do not use `main` in smoke checks, fallback validation, or transcript task
  probes for this service slice.

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

## OpenHands shadow Qwen-Agent lane
Experimental shadow alias:
- alias: `code-qwen-agent`
- backend target: Mini-local `qwen-agent-proxy`
- intended upstream model: `qwen-agent-coder-next-shadow`
- contract shape: Chat Completions-first ordinary, `required`, and named tool use
- unsupported/out of contract:
  - streaming
  - `/v1/responses`
  - MCP access

Shadow-worker verification:
```bash
OPENHANDS_WORKER_SHADOW_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key_shadow)
OPENHANDS_LITELLM_SHADOW_BASE_URL=${OPENHANDS_LITELLM_SHADOW_BASE_URL:-http://127.0.0.1:4001/v1}

curl -fsS "${OPENHANDS_LITELLM_SHADOW_BASE_URL}/models" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_SHADOW_KEY}" | jq .

curl -fsS "${OPENHANDS_LITELLM_SHADOW_BASE_URL}/model/info" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_SHADOW_KEY}" | jq .

curl -fsS "${OPENHANDS_LITELLM_SHADOW_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_SHADOW_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"code-qwen-agent",
    "messages":[{"role":"user","content":"Call noop once with {\"value\":\"x\"}."}],
    "tools":[{"type":"function","function":{"name":"noop","description":"noop","parameters":{"type":"object","properties":{"value":{"type":"string"}},"required":["value"],"additionalProperties":false}}}],
    "tool_choice":{"type":"function","function":{"name":"noop"}},
    "stream":false,
    "max_tokens":128
  }' | jq .
```

Expected:
- `/models` returns only `code-qwen-agent`
- chat completions returns one populated `tool_calls` entry
- named and `required` tool modes fail closed if the adapter does not return a callable function object
- `/v1/responses` remains unavailable on the shadow alias

Current verified caveat on LiteLLM `1.83.4`:
- `/v1/model/info` and `/model/info` return `403` for worker-scoped shadow keys
  on the `4001` instance.
- LiteLLM normalizes the supplied route list to `["llm_api_routes"]`, and that
  route group does not include model-info endpoints here.
- Master-key access to `/v1/model/info` on `4001` is healthy; this is a worker
  key policy gap, not a sidecar or backend failure.

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
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local
curl -fsS http://127.0.0.1:4000/v1/search/searxng-search \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"openvino llm","max_results":3}' | jq .
```

Note:
- `/v1/search/searxng-search` remains for direct callers and MCP tools.
- Open WebUI web search is configured in Open WebUI itself and does not depend on LiteLLM prompt-shape or schema middleware.
