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

### Router baseline check (required before tuning)
Verify the router plugin is active and not silently degrading to direct model usage:
```bash
rg -n "Error in router plugin|Falling back to direct model usage|Router predicted approach" \
  /Users/thestudio/Library/Logs/optillm-proxy.log \
  /Users/thestudio/Library/Logs/optillm-proxy.err \
  | tail -n 80
```
Expected:
- No `Error in router plugin` / `Falling back to direct model usage` lines after restart.
- At least one `Router predicted approach: ...` line after a `router` request.

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

Canary trio planner check:
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost-plan-trio","messages":[{"role":"user","content":"Draft a rollback-first deployment plan in 5 bullets."}],"max_tokens":256}' \
  | jq -r '.choices[0].message.content'
```

### Trio canary A/B gate (`boost-plan` vs `boost-plan-trio`)
Run from Mini:
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
./scripts/canary_plansearch_profiles.py \
  --url http://127.0.0.1:4000/v1/chat/completions \
  --bearer "$LITELLM_API_KEY" \
  --model-a boost-plan \
  --model-b boost-plan-trio \
  --max-tokens 160 \
  --out-json /tmp/plansearchtrio_canary.json
```
Gate policy (current):
- Candidate empty outputs must be zero.
- Candidate sentinel error text outputs must be zero.
- Candidate p95 latency must be `<= 1.75x` baseline (`boost-plan`) on the same prompt fixture.
- Script exits non-zero when the gate fails.

Compact Trio gate run (recommended for current canary):
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
./scripts/canary_plansearch_profiles.py \
  --url http://127.0.0.1:4000/v1/chat/completions \
  --bearer "$LITELLM_API_KEY" \
  --model-a boost-plan \
  --model-b boost-plan-trio \
  --model-b-extra-json '{"plansearchtrio_mode":"auto","plansearchtrio_latency_budget_ms":17000,"plansearchtrio_reasoning_effort_synthesis":"high","plansearchtrio_reasoning_effort_rewrite":"high"}' \
  --max-tokens 160 \
  --out-json /tmp/plansearchtrio_canary_compact.json
```

Reasoning-effort note:
- Trio applies stage-scoped reasoning effort only for deep `synthesis`/`rewrite`.
- If the backend rejects `reasoning_effort`, trio retries the stage once without it.

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

Deploy behavior:
- Checks out the exact local git SHA on Studio in detached HEAD mode.
- Runs `uv sync --frozen` before restart.
- Uses the configured OptiLLM API key for authenticated smokes.
- Requires Studio working tree at `/Users/thestudio/optillm-proxy` to be an
  initialized git repo (`.git` present); deploy preflight now fails fast if missing.

Overrides (all optional):
- `OPTILLM_STUDIO_HOST` (default: `studio`)
- `OPTILLM_LAUNCHD_LABEL` (default: `com.bebop.optillm-proxy`)
- `OPTILLM_STUDIO_UTILITY_WRAPPER` (default: repo `platform/ops/scripts/studio_run_utility.sh`)
- `OPTILLM_API_KEY_ENV` (default: `/etc/optillm-proxy/env`)
- `OPTILLM_SMOKE_MODEL` (default: `mlx-gpt-oss-120b-mxfp4-q4`)
- `OPTILLM_SMOKE_APPROACH` (default: `bon`)
- `OPTILLM_SMOKE_MAX_TOKENS` (default: `32`)
- `OPTILLM_RUN_BENCH=1` to run a benchmark after deploy
- `OPTILLM_BENCH_MODEL` (default: `p-plan-max`)
- `OPTILLM_BENCH_PROMPT` (default prompt defined in script)
- `OPTILLM_BENCH_MAX_TOKENS` (default: `1200`)

## Studio scheduling policy
- This label is inference lane and must not be background-throttled.
- Required plist scheduling key: `ProcessType = Interactive`.
- Forbidden inference keys: positive `Nice`, `LowPriorityIO`, `LowPriorityBackgroundIO`.
- Policy and audit tooling:
  - `docs/foundation/studio-scheduling-policy.md`
  - `platform/ops/scripts/enforce_studio_launchd_policy.py`
  - `platform/ops/scripts/audit_studio_scheduling.py`
