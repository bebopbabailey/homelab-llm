# Inference Layer Runbook

Scope: inference backend health checks and safe restarts.

## OpenVINO server (Mini)
```bash
sudo systemctl restart ov-server.service
journalctl -u ov-server.service -n 200 --no-pager
curl -fsS http://127.0.0.1:9000/health | jq .
```

## Studio lanes
Read-only checks:
```bash
ssh studio "curl -fsS http://127.0.0.1:8101/v1/models | jq ."
ssh studio "curl -fsS http://127.0.0.1:8126/v1/models | jq ."
ssh studio "mlxctl status --checks"
./platform/ops/scripts/mlxctl studio-cli-sha
```

Mini-side LAN reachability:
```bash
for p in 8101 8126; do
  curl -fsS "http://192.168.1.72:${p}/v1/models" | jq .
done
```

Notes:
- `8100` and `8102` are retired GPT rollback lanes and are not active health
  targets.
- Current public MLX truth is `8101`.
- Current public GPT `llmster` truth is `8126`.
