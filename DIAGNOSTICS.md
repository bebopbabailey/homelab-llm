# Diagnostics (Read‑Only)

Use these to gather facts without changing system state.

## Service status (Mini)
```bash
systemctl status litellm-orch.service open-webui.service ov-server.service searxng.service grafana-server.service prometheus.service --no-pager
```

## Logs (Mini)
```bash
journalctl -u litellm-orch.service -n 200 --no-pager
journalctl -u open-webui.service -n 200 --no-pager
journalctl -u ov-server.service -n 200 --no-pager
journalctl -u searxng.service -n 200 --no-pager
journalctl -u grafana-server.service -n 200 --no-pager
journalctl -u prometheus.service -n 200 --no-pager
```

## Health checks (Mini)
```bash
curl -sS http://127.0.0.1:4000/health/readiness
curl -sS http://127.0.0.1:3000/health
curl -sS http://127.0.0.1:9000/health
```

## Ports  
```bash
ss -lntp
```

## Submodules
```bash
git submodule status
```
