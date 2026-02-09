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

## Auth reminder
- OptiLLM requires `Authorization: Bearer <OPTILLM_API_KEY>` for all requests, even from localhost.
- Missing headers return `Invalid Authorization header`.

### Confirm approach usage
OptiLLM already logs the selected approaches at INFO level. Look for:
```
Using approach(es) [...]
```
Quick filter:
```bash
journalctl -u optillm-proxy.service -n 200 --no-pager | rg -n "Using approach\\(es\\)"

### Streaming benchmark (TTFT + total time)

```bash
layer-gateway/optillm-proxy/scripts/bench_stream.py \
  --model p-plan-max \
  --prompt "Write a detailed migration plan with risks and rollbacks." \
  --max-tokens 1200
```
```

## Update OptiLLM (upstream release)
1) Update the pin in `pyproject.toml`.
2) Reinstall and restart:
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
uv sync
sudo systemctl restart optillm-proxy.service
```

## Rebuild the venv (if needed)
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
rm -rf .venv
uv venv .venv
uv sync
sudo systemctl restart optillm-proxy.service
```


## Studio deploy (launchd)
Use the deploy helper from the Mini (source of truth):
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
./scripts/deploy_studio.sh
```

Overrides (all optional):
- `OPTILLM_STUDIO_HOST` (default: `studio`)
- `OPTILLM_LAUNCHD_LABEL` (default: `optillm.proxy.studio`)
- `OPTILLM_API_KEY_ENV` (default: `/etc/optillm-proxy/env`)
- `OPTILLM_SMOKE_MODEL` (default: `mlx-gpt-oss-120b-mxfp4-q4`)
- `OPTILLM_SMOKE_APPROACH` (default: `bon`)
- `OPTILLM_SMOKE_MAX_TOKENS` (default: `32`)
- `OPTILLM_RUN_BENCH=1` to run a benchmark after deploy
- `OPTILLM_BENCH_MODEL` (default: `p-plan-max`)
- `OPTILLM_BENCH_PROMPT` (default prompt defined in script)
- `OPTILLM_BENCH_MAX_TOKENS` (default: `1200`)
