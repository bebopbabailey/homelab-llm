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

## Local trace stack
Install package-managed Alloy and Tempo on the Mini:
```bash
sudo apt-get update
sudo apt-get install -y alloy tempo
```

Deploy repo-managed config:
```bash
sudo install -d -m 0755 /etc/homelab-llm/grafana/provisioning/datasources
sudo install -m 0644 services/grafana/config/alloy.river /etc/homelab-llm/grafana/alloy.river
sudo install -m 0644 services/grafana/config/tempo.yaml /etc/homelab-llm/grafana/tempo.yaml
sudo install -m 0644 services/grafana/provisioning/datasources/tempo.yml /etc/homelab-llm/grafana/provisioning/datasources/tempo.yml
```

Configure package services to use repo-managed config:
```bash
sudo install -d -m 0755 /etc/systemd/system/alloy.service.d /etc/systemd/system/tempo.service.d
sudo tee /etc/systemd/system/alloy.service.d/10-homelab.conf >/dev/null <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/alloy run --server.http.listen-addr=127.0.0.1:12345 /etc/homelab-llm/grafana/alloy.river
EOF
sudo tee /etc/systemd/system/tempo.service.d/10-homelab.conf >/dev/null <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/tempo -config.file=/etc/homelab-llm/grafana/tempo.yaml
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now tempo.service alloy.service
sudo systemctl restart grafana-server.service
```

Trace-stack health:
```bash
curl -fsS http://127.0.0.1:3200/ready
curl -fsS http://127.0.0.1:12345/-/ready
ss -ltnp '( sport = :4317 or sport = :4318 or sport = :14317 or sport = :14318 or sport = :3200 )'
```

Expected listeners are localhost-only:
- Alloy OTLP: `127.0.0.1:4317`, `127.0.0.1:4318`
- Tempo internal OTLP: `127.0.0.1:14317`, `127.0.0.1:14318`
- Tempo query API: `127.0.0.1:3200`

Tempo stores span attributes with `max_attribute_bytes: 16384` so the local
LLM prompt/response capture cap is enforced at the backend as well as in the
Python helper.

Rollback:
```bash
sudo systemctl disable --now alloy.service tempo.service
sudo rm -f /etc/systemd/system/alloy.service.d/10-homelab.conf
sudo rm -f /etc/systemd/system/tempo.service.d/10-homelab.conf
sudo rm -f /etc/homelab-llm/grafana/alloy.river /etc/homelab-llm/grafana/tempo.yaml
sudo rm -f /etc/homelab-llm/grafana/provisioning/datasources/tempo.yml
sudo systemctl daemon-reload
sudo systemctl restart grafana-server.service
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
