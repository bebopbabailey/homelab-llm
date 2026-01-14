# Runbook: SearXNG

## Start/stop
```bash
sudo systemctl start searxng.service
sudo systemctl stop searxng.service
sudo systemctl restart searxng.service
```

## Logs
```bash
journalctl -u searxng.service -f
```

## Health
```bash
curl http://127.0.0.1:8888
```
