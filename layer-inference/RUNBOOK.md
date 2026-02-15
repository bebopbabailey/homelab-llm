# Inference Layer Runbook

Scope: inference backend health checks and safe restarts (host-specific).

## OpenVINO server (Mini)
```bash
sudo systemctl restart ov-server.service
journalctl -u ov-server.service -n 200 --no-pager
curl -fsS http://127.0.0.1:9000/health | jq .
```

## MLX Omni (Studio)
Read-only checks on Studio:
```bash
ssh studio "curl -fsS http://127.0.0.1:8100/v1/models | jq ."
ssh studio "mlxctl status"
```

