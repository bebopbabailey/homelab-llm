# Runbook: Open WebUI

## Start/stop
```bash
sudo systemctl start open-webui.service
sudo systemctl stop open-webui.service
sudo systemctl restart open-webui.service
```

## Logs
```bash
journalctl -u open-webui.service -f
```

## Health
```bash
curl http://127.0.0.1:3000/health
```
