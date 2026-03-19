# Runbook: llama-cpp-server

## Status
- Canonical GPT service boundary for `fast` / `deep` rollout.
- Current posture:
  - `fast` is live on shared `8126`
  - `deep` is live on shared `8126` under the usable-success contract
  - old MLX GPT rollback lanes on `8100` and `8102` are retired and unloaded

## Intended runtime
- Host: Studio
- Label: `com.bebop.llmster-gpt.8126`
- Bind: `192.168.1.72:8126`
- Public caller contract: LiteLLM-only via `fast` and `deep`
- Raw truth-path mirrors:
  - `fast` mirror -> `127.0.0.1:8130`
  - `deep` mirror -> `127.0.0.1:8131`

## Storage policy
- Keep only:
  - active runtime models
  - runtime metadata required by the active services
- When a future GPT cutover is in progress, temporarily allow one staged next
  artifact. Otherwise keep only the active runtime models and runtime metadata.

## Planned checks
Thin daemon-aware bootstrap template:
```bash
python3 /Users/thestudio/bin/llmster_ensure_server.py \
  --lms-bin /Users/thestudio/.lmstudio/llmster/0.0.7-4/.bundle/lms \
  --bind 192.168.1.72 \
  --port 8126 \
  --api-key-env LLMSTER_API_KEY \
  --load-spec 'gpt-oss-20b|llmster-gpt-oss-20b-mxfp4-gguf|32768|4'
```

Measured dual-load preflight:
```bash
/Users/thestudio/.lmstudio/bin/lms load gpt-oss-20b \
  --identifier llmster-gpt-oss-20b-mxfp4-gguf \
  --context-length 32768 \
  --parallel 4 \
  --estimate-only -y

/Users/thestudio/.lmstudio/bin/lms load gpt-oss-120b \
  --identifier llmster-gpt-oss-120b-mxfp4-gguf \
  --context-length 32768 \
  --parallel 2 \
  --estimate-only -y
```

Server surface:
```bash
curl -fsS http://192.168.1.72:8126/v1/models | jq .
```

Raw mirror probes:
```bash
curl -fsS http://127.0.0.1:8130/v1/models | jq .
curl -fsS http://127.0.0.1:8131/v1/models | jq .
```

Raw mirror launcher invariants:
- use a versioned raw `llama-server` path when available
- use `--jinja`
- do not add repetition penalties for GPT-OSS

LiteLLM alias probes:
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"fast","messages":[{"role":"user","content":"Reply with exactly: fast-ok"}],"stream":false,"max_tokens":32}' | jq .

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"deep","messages":[{"role":"user","content":"Reply with exactly: deep-ok"}],"stream":false,"max_tokens":32}' | jq .
```

Acceptance focus:
- plain chat
- structured simple output
- structured nested output
- non-stream auto tool use
- constrained tool use (`required` and named-tool force)
- large-schema tool-call integrity as a diagnostic seam
- concurrency / parallel serving behavior
- OpenAI-compatible serving behavior

Evidence order used for the accepted `deep` cutover:
1. close `fast` observation on the current live LM Studio stack
2. refresh raw standalone llama.cpp and compare while live `llmster` remained untouched
3. refresh LM Studio daemon/runtime
4. rerun the `fast` regression gate
5. stage/import `deep`, prove shared posture, validate the temporary canary alias, and
   repoint canonical public `deep`

Deep usable-success rule:
- plain chat clean
- structured simple clean
- structured nested clean
- auto noop strong
- auto arg-bearing usable at `>= 8/10` on direct `llmster` and public LiteLLM
- at least one constrained mode strong:
  - `tool_choice="required" >= 9/10`, or
  - named-tool forcing `>= 9/10`
- crashes, listener loss, sustained readiness regressions, repeated `5xx`, and
  repeated timeouts remain blockers

Shared-posture proof before any public `deep` cutover on `8126`:
```bash
ssh studio '/Users/thestudio/.lmstudio/bin/lms ps --json'
ssh studio 'curl -fsS http://192.168.1.72:8126/v1/models | jq .'
ssh studio 'memory_pressure -Q'
ssh studio 'vm_stat'
ssh studio 'top -l 1 -stats pid,command,mem,cpu'
sleep 300
ssh studio 'memory_pressure -Q'
ssh studio 'vm_stat'
ssh studio 'top -l 1 -stats pid,command,mem,cpu'
```

Shared-posture pass means:
- both intended models are still loaded and visible in `lms ps --json`
- both intended models are visible in `/v1/models`
- no TTL / auto-evict ambiguity exists for canonical `fast` / `deep`
- `fast` stays healthy under the actual dual-load posture

OpenAI gpt-oss verification:
- use the official upstream verification flow from:
  `https://developers.openai.com/cookbook/articles/gpt-oss/verifying-implementations`
- minimum one verification pass on refreshed raw deep mirror
- minimum one verification pass on direct `llmster` deep
- public LiteLLM deep verification is optional and advisory in this slice

Historical cutover note:
- the temporary Mini-side canary alias was used before repointing
  canonical public `deep`
- it is not part of the active canonical runtime surface

Current locked shared-`8126` result:
- public `deep` plain chat `5/5`
- public `deep` structured simple `5/5`
- public `deep` structured nested `5/5`
- public `deep` auto noop `10/10`
- public `deep` auto arg-bearing `10/10`
- public `deep` required arg-bearing `9/10`
- named forced-tool choice unsupported on current backend path

## Rollback
- Repoint `fast` / `deep` back to their current MLX upstreams.
- Stop the raw mirrors by PID and delete the staged non-canonical artifacts.
- Disable `com.bebop.llmster-gpt.8126` only after the Mini aliases have been
  rolled back.
