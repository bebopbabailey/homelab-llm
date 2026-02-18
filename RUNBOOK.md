# Runbook: OptiLLM Proxy

Scope note: this runbook covers the **Studio launchd** deployment for the
OptiLLM proxy used by LiteLLM’s `boost` handle.

## Start/stop
```bash
# Studio (launchd)
sudo launchctl kickstart -k system/com.bebop.optillm-proxy

# show status/details
sudo launchctl print system/com.bebop.optillm-proxy | sed -n '1,200p'

# unload/load (rare)
sudo launchctl bootout system /Library/LaunchDaemons/com.bebop.optillm-proxy.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.bebop.optillm-proxy.plist
```

## Logs
```bash
# Studio logs (as configured by plist)
tail -n 200 -f /Users/thestudio/Library/Logs/optillm-proxy.log
tail -n 200 -f /Users/thestudio/Library/Logs/optillm-proxy.err
```

## Identity and configuration (Studio)
- LaunchDaemon: `/Library/LaunchDaemons/com.bebop.optillm-proxy.plist`
- Label: `com.bebop.optillm-proxy`
- Listener: `0.0.0.0:4020`
- Upstream (current): Mini LiteLLM via tailnet TCP forward (`http://100.69.99.60:4443/v1`)

Do not commit secrets: the plist contains `--optillm-api-key` and may also set
`OPENAI_API_KEY`. Keep real values out of git.

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
rg -n "Using approach\\(es\\)" /Users/thestudio/Library/Logs/optillm-proxy.log | tail -n 50

# if you need to inspect current effective args
sudo launchctl print system/com.bebop.optillm-proxy \
  | rg -n "ProgramArguments|4020|base-url|approach|model" \
  | head -n 80
```

## Health / smoke checks

### Studio: direct proxy check
```bash
curl -fsS http://127.0.0.1:4020/v1/models \
  -H "Authorization: Bearer $OPTILLM_API_KEY" \
  | jq -r '.data[].id' | head
```

### Mini: through LiteLLM `boost`
Preferred check (keeps clients LiteLLM-only):
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost","messages":[{"role":"user","content":"ping"}],"optillm_approach":"bon","max_tokens":16}' \
  | jq -r '.choices[0].message.content'
```

Deep lane check:
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost-deep","messages":[{"role":"user","content":"ping"}],"optillm_approach":"router","max_tokens":32}' \
  | jq -r '.choices[0].message.content'
```

### Streaming benchmark (TTFT + total time)

```bash
layer-gateway/optillm-proxy/scripts/bench_stream.py \
  --model p-plan-max \
  --prompt "Write a detailed migration plan with risks and rollbacks." \
  --max-tokens 1200
```

## Update OptiLLM (upstream release)
1) Update the pin in `pyproject.toml`.
2) Reinstall and restart:
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
uv sync
# Studio: restart launchd service
sudo launchctl kickstart -k system/com.bebop.optillm-proxy
```

## Rebuild the venv (if needed)
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
rm -rf .venv
uv venv .venv
uv sync
# Studio: restart launchd service
sudo launchctl kickstart -k system/com.bebop.optillm-proxy
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
