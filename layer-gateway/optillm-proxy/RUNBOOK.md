# Runbook: OptiLLM Proxy

## Start/stop
```bash
sudo systemctl start optillm-proxy.service
sudo systemctl stop optillm-proxy.service
sudo systemctl restart optillm-proxy.service
```

## Logs
```bash
journalctl -u optillm-proxy.service -f
```
