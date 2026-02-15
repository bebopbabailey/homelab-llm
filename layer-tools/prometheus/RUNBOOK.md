# Runbook: Prometheus

## Start/stop (Mini)
```bash
sudo systemctl restart prometheus.service
journalctl -u prometheus.service -n 200 --no-pager
```

## Health
```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9090/-/healthy
```

