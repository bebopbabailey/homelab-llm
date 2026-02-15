# Interface Layer Runbook

Scope: interface-only checks and safe restarts (Mini).

## Health checks (Mini)
```bash
curl -fsS http://127.0.0.1:3000/health
curl -fsS http://127.0.0.1:3001/api/health
```

## Start/stop (Mini)
```bash
sudo systemctl restart open-webui.service
sudo systemctl restart grafana-server.service
```

## Logs (Mini)
```bash
journalctl -u open-webui.service -n 200 --no-pager
journalctl -u grafana-server.service -n 200 --no-pager
```

