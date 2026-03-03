# 2026-03-03 — Web-search trail recovery and Phase 2 re-entry

## Summary
- Recovered from a transient Studio reachability outage that caused Open WebUI requests to appear hung due to upstream lane timeouts.
- Re-validated service and lane health end-to-end.
- Confirmed gateway chat paths (`fast`, `main`, `deep`, `boost`) are responding again.
- Prepared a fresh Phase A run-id for user-driven Open WebUI validation.

## Incident context
- During outage window, `192.168.1.72` became unreachable and LiteLLM logged upstream connection failures/cooldowns for `main`/`deep` lanes.
- After host recovery, all three team lanes (`8100`, `8101`, `8102`) report healthy with `http_models_ok=True`.

## Commands run (recovery validation)
```bash
date '+%F %T %Z'
systemctl is-active open-webui.service litellm-orch.service websearch-orch.service searxng.service
mlxctl status --checks

curl -m 4 http://192.168.1.72:8100/v1/models
curl -m 4 http://192.168.1.72:8101/v1/models
curl -m 4 http://192.168.1.72:8102/v1/models

curl -fsS http://127.0.0.1:3000/health
curl -fsS http://127.0.0.1:4000/health/readiness
curl -fsS http://127.0.0.1:8899/health
curl -fsS "http://127.0.0.1:8888/search?q=moon+phase&format=json"

source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" -H 'Content-Type: application/json' \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"fast","stream":false,"messages":[{"role":"user","content":"Reply with exactly: fast-ok"}],"max_tokens":64}'
curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" -H 'Content-Type: application/json' \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"main","stream":false,"messages":[{"role":"user","content":"Reply with exactly: main-ok"}],"max_tokens":24}'
curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" -H 'Content-Type: application/json' \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"deep","stream":false,"messages":[{"role":"user","content":"Reply with exactly: deep-ok"}],"max_tokens":64}'
curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" -H 'Content-Type: application/json' \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"boost","stream":false,"messages":[{"role":"user","content":"Reply with exactly: boost-ok"}],"max_tokens":24}'

curl -fsS "http://127.0.0.1:8899/search?q=I+need+help+learning+how+to+cook+with+a+wok&format=json"
curl -fsS -X POST http://127.0.0.1:8899/web_loader \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://en.wikipedia.org/wiki/Wok","https://en.wikipedia.org/wiki/Stir_frying"]}'

journalctl -u open-webui.service --since "20 minutes ago" --no-pager | rg -n "ERROR|Exception|Traceback|JSONResponse object is not subscriptable|No search query generated"
journalctl -u litellm-orch.service --since "20 minutes ago" --no-pager | rg -n "InternalServerError: OpenAIException - Connection error|RouterRateLimitError|No deployments available|APIConnectionError|timeout"
journalctl -u websearch-orch.service --since "20 minutes ago" --no-pager
```

## Results
- Service health: all active.
- Lane health: `8100/8101/8102` all reachable and serving `/v1/models`.
- LiteLLM chat smokes:
  - `fast` => `fast-ok`
  - `main` => `main-ok`
  - `deep` => `deep-ok`
  - `boost` => `boost-ok`
- `websearch-orch` search request completed with non-empty results and rerank/trust/citation/grounding telemetry in logs.
- `web_loader` completed with `ok=2`, `errors=0`, extraction/cap telemetry present.
- No fresh Open WebUI traceback for `JSONResponse object is not subscriptable`.
- No fresh LiteLLM upstream connection/cooldown error pattern in the immediate recovery validation window.

## Phase A re-entry status
- Generated run-id: `RECOVERY-20260303-A`.
- Query pack printed, but not yet executed in Open WebUI.
- Scoring currently reports `0/10` seen for that run-id until those prompts are run in OWUI with markers.

## Notes
- Direct local call to `http://127.0.0.1:3000/api/chat/completions` returns `401 Not authenticated`, so end-user flow validation remains OWUI session-driven.
