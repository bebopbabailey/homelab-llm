# Gateway Layer Runbook

Scope: gateway-only checks and safe restarts (Mini + Studio pointers).

## LiteLLM (Mini)
```bash
sudo systemctl restart litellm-orch.service
journalctl -u litellm-orch.service -n 200 --no-pager
curl -fsS http://127.0.0.1:4000/health/readiness -H "Authorization: Bearer $LITELLM_API_KEY" | jq .
```

## Boost lane (Mini -> Studio)
Preferred: test through LiteLLM handle `boost` (requires bearer auth).
See `docs/foundation/testing.md`.

## SearXNG (Mini)
```bash
sudo systemctl restart searxng.service
journalctl -u searxng.service -n 200 --no-pager
curl -fsS "http://127.0.0.1:8888/search?q=ping&format=json" | jq .
```
