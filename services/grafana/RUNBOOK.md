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

## Tailnet Operator Access
Desired state:
```bash
tailscale serve --yes --bg --service=svc:grafana http://127.0.0.1:3001
```

Verification:
```bash
tailscale serve status --json
curl -I -sS https://grafana.tailfd1400.ts.net/
```

Expected:
- `Services["svc:grafana"]` proxies `https://grafana.tailfd1400.ts.net/` to `http://127.0.0.1:3001`
- local `GET /api/health` returns `200`
- remote tailnet `GET /` returns `302` to `/login`

Rollback:
```bash
tailscale serve reset --yes --service=svc:grafana
```
