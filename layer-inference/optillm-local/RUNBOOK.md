# Runbook — OptiLLM Local (Orin)

## Install (Orin)
```bash
sudo mkdir -p /opt/homelab
sudo chown -R $USER:$USER /opt/homelab
cd /opt/homelab
# clone monorepo (source of truth)
# git clone <repo> optillm-local
```

Service directory:
```
/opt/homelab/optillm-local/layer-inference/optillm-local
```

## Env file
```bash
sudo mkdir -p /etc/optillm-local
sudo cp config/env.example /etc/optillm-local/env
sudo chmod 640 /etc/optillm-local/env
```

## systemd unit
```bash
sudo cp systemd/optillm-local.service /etc/systemd/system/optillm-local.service
# runs as user: christopherbailey
sudo systemctl daemon-reload
sudo systemctl enable --now optillm-local.service
```

## Logs
```bash
journalctl -u optillm-local.service -n 200 --no-pager
```

## Smoke test
```bash
curl -fsS http://127.0.0.1:4040/v1/models \
  -H "Authorization: Bearer $OPTILLM_API_KEY" | jq .
```

## Deploy (from Mini)
```bash
platform/ops/scripts/deploy-optillm-local-orin.sh
```
