# 2026-02-25 — Swap alias vLLM-metal canary smoke pass

## Goal
Keep the `swap` canary frozen and verify it remains healthy end-to-end through LiteLLM and OpenWebUI-facing APIs.

## What we validated
- LiteLLM still exposes `swap` in `/v1/models`.
- `swap` request path returns `HTTP 200` from `POST /v1/chat/completions`.
- LiteLLM routes `swap` to the Mini tunnel target `http://127.0.0.1:19400/v1`.
- Studio canary (`vllm-metal`) is live on `127.0.0.1:18400` and serves `default_model`.

## Evidence commands
```bash
curl -fsS -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://127.0.0.1:4000/v1/models
curl -sS -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  --data-binary @/tmp/swap_probe.json http://127.0.0.1:4000/v1/chat/completions
ssh studio 'curl -fsS http://127.0.0.1:18400/v1/models'
journalctl -u litellm-orch.service -n 120 --no-pager
```

## Result
- Status: PASS (FAST verification)
- Outcome: `swap` canary is stable enough to keep as the active test lane while leaving `main/deep/fast` unchanged.
