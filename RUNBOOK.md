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

## Experimental alias checks
```bash
rg -n "metal-test-fast|metal-test-main|metal-test-deep" \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
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

rg -n "websearch-schema|websearch_schema_guardrail|web_answer|fast-research" \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/SERVICE_SPEC.md \
  /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/docs/openwebui.md
```

Expected:
- `fast`, `main`, `deep`, and `boost*` aliases appear in `/v1/models`.
- `fast-research` is absent.
- No LiteLLM config references remain for `websearch-schema`, `websearch_schema_guardrail`, or `web_answer`.
- Current resilience baseline keeps `fast -> main`.

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
