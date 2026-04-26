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

## Rollback
There is no pre-approved rollback to retired `8100` or `8102` GPT lanes.
If shared `8126` must be abandoned, treat the next target as a new rollout that
requires fresh validation and canonical doc updates before public reuse.
