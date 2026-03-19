# Interface Layer Runbook

Scope: interface-only checks and safe restarts (Mini).

## Health checks (Mini)
```bash
curl -fsS http://127.0.0.1:3000/health
curl -fsS http://127.0.0.1:3001/api/health
```

## Health checks (Orin speech appliance)
```bash
curl -fsS http://192.168.1.93:18080/health
curl -fsS http://192.168.1.93:18080/health/readiness | jq .
```

Control-plane quick checks:
```bash
curl -fsS http://192.168.1.93:18080/ops >/dev/null
curl -fsS http://192.168.1.93:18080/ops/api/registry/curated \
  -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq '.count'
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

## Logs (Orin)
```bash
ssh orin "journalctl -u voice-gateway.service -n 200 --no-pager"
ssh orin "journalctl -u voice-gateway-native-stt.service -n 200 --no-pager"
```
