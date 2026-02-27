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
curl http://127.0.0.1:4000/health
curl http://127.0.0.1:4000/health/readiness
curl http://127.0.0.1:4000/health/liveliness
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
# Verify request mutation is allowed
rg -n "modify_params" /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml

# Verify GPT-lane target aliases are configured and stream coercion is disabled
rg -n "target_models|coerce_stream_false" /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml
```

## GPT streaming checks (pass-through)
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

# Stream should pass through for GPT lanes (deep/fast/boost) when stream=true.
curl -N -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"fast","stream":true,"messages":[{"role":"user","content":"Reply with exactly: stream-ok"}],"max_tokens":32}'

# Non-stream remains available per call when explicitly requested.
curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"fast","stream":false,"messages":[{"role":"user","content":"Reply with exactly: nonstream-ok"}],"max_tokens":32}' | jq .
```
