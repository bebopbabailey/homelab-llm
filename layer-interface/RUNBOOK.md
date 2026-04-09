# Interface Layer Runbook

Scope: interface-only checks and safe restarts for Mini-hosted UI services plus
the Orin-hosted `voice-gateway`.

## Health checks (Mini)
```bash
curl -fsS http://127.0.0.1:3000/health
curl -fsS http://127.0.0.1:3001/api/health
curl -I -sS http://127.0.0.1:4096/ | sed -n '1,5p'
```

## Health checks (Orin speech appliance)
```bash
curl -fsS http://192.168.1.93:18080/health
curl -fsS http://192.168.1.93:18080/health/readiness | jq .
```

## Start/stop (Mini)
```bash
sudo systemctl restart open-webui.service
sudo systemctl restart grafana-server.service
sudo systemctl restart opencode-web.service
```

## Logs (Mini)
```bash
journalctl -u open-webui.service -n 200 --no-pager
journalctl -u grafana-server.service -n 200 --no-pager
journalctl -u opencode-web.service -n 200 --no-pager
```

## Logs (Orin)
```bash
ssh orin "journalctl -u voice-gateway.service -n 200 --no-pager"
ssh orin "journalctl -u voice-gateway-native-stt.service -n 200 --no-pager"
```
