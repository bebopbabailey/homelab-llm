# Runbook: llama-cpp-server

## Scope
Canonical GPT service boundary for `fast` and `deep` rollout.

## Current runtime
- `fast` is live on shared `8126`
- `deep` is live on shared `8126`
- public caller contract remains LiteLLM-only

## Health checks
```bash
ssh studio 'curl -fsS http://192.168.1.72:8126/v1/models | jq .'
ssh studio 'curl -fsS http://192.168.1.72:8126/api/v1/models | jq .'
ssh studio 'curl -fsS http://192.168.1.72:8126/v1/responses -H "Content-Type: application/json" -d "{\"model\":\"llmster-gpt-oss-20b-mxfp4-gguf\",\"input\":\"Reply with exactly: responses-ok\",\"reasoning\":{\"effort\":\"low\"}}" | jq .'
```

Direct Responses follow-up/state check:
```bash
python3 - <<'PY'
import json, urllib.request

base = "http://192.168.1.72:8126/v1/responses"
headers = {"Content-Type": "application/json"}
initial = {
    "model": "llmster-gpt-oss-120b-mxfp4-gguf",
    "input": "Rewrite this naturally: um okay this matters a lot actually",
    "reasoning": {"effort": "low"},
    "max_output_tokens": 256,
}
req = urllib.request.Request(base, data=json.dumps(initial).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=90) as resp:
    first = json.loads(resp.read().decode())

followup = {
    "model": "llmster-gpt-oss-120b-mxfp4-gguf",
    "previous_response_id": first["id"],
    "input": "Make that more formal.",
    "reasoning": {"effort": "low"},
    "max_output_tokens": 128,
}
req = urllib.request.Request(base, data=json.dumps(followup).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=90) as resp:
    second = json.loads(resp.read().decode())

print(json.dumps(
    {
        "first_id": first.get("id"),
        "second_previous_response_id": second.get("previous_response_id"),
        "first_cached_tokens": ((first.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens"),
        "second_cached_tokens": ((second.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens"),
        "second_output_text": second.get("output_text"),
        "second_output": second.get("output"),
    },
    indent=2,
))
PY
```

Expected:
- initial response returns a stable response `id`
- follow-up response echoes that value in `previous_response_id`
- `usage.input_tokens_details.cached_tokens` is present on both responses
- usable final assistant text is always recoverable from the `output` message
  surface even when raw `output_text` is null

## Rollback
There is no pre-approved rollback to retired `8100` or `8102` GPT lanes.
If shared `8126` must be abandoned, treat the next target as a new rollout that
requires fresh validation and canonical doc updates before public reuse.
