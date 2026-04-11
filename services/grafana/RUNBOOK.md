# Runbook: Grafana

## Start/stop (Mini)
```bash
sudo systemctl start grafana-server.service
sudo systemctl stop grafana-server.service
sudo systemctl restart grafana-server.service
```

## Logs (Mini)
```bash
journalctl -u grafana-server.service -n 200 --no-pager
```

## Health
```bash
curl -fsS http://127.0.0.1:3001/api/health | jq .
```

