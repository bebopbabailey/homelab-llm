# TINYAGENTS_PLAN

## Phases (compact)
- Phase 0: repo skeleton, env template, smoke tests, verify LiteLLM health/models.
- Phase 1: minimal LiteLLM client, model list validation, request ID logging.
- Phase 2: orchestration MVP (deterministic routing, task retries).
- Phase 3: ops readiness (config validation, log correlation, runbook).
- Phase 4: optional metadata enrichment (no new ports).

## Tasks (minimal)
- [ ] Repo skeleton + docs
- [ ] Env template
- [ ] Smoke tests
- [ ] LiteLLM health/models verified

## Smoke tests (short)
```bash
curl -fsS http://127.0.0.1:4000/health | jq .
curl -fsS http://127.0.0.1:4000/v1/models | jq -e '.data | length > 0'
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"jerry-weak","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq -e '.choices | length > 0'
curl -fsS http://127.0.0.1:9000/health | jq .
curl -fsS http://127.0.0.1:3000/health | jq .
curl -fsS http://192.168.1.72:8100/v1/models | jq .
```
