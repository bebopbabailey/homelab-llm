# Inference Layer Runbook

Scope: inference backend health checks and safe restarts (host-specific).

## OpenVINO server (Mini)
```bash
sudo systemctl restart ov-server.service
journalctl -u ov-server.service -n 200 --no-pager
curl -fsS http://127.0.0.1:9000/health | jq .
```

## MLX lanes (Studio)
Read-only checks on Studio:
```bash
# Required active listener check (current default lane)
ssh studio "curl -fsS http://127.0.0.1:8100/v1/models | jq ."

# Optional checks (only if assigned for active experiments or cutovers)
# ssh studio "curl -fsS http://127.0.0.1:8101/v1/models | jq ."
# ssh studio "curl -fsS http://127.0.0.1:8102/v1/models | jq ."

ssh studio "mlxctl status"
ssh studio "mlxctl status --checks"
ssh studio "mlxctl verify"
```

Team-lane boot launcher (`com.bebop.mlx-launch`) is now expected to launch
`vllm-metal` (`vllm serve`) for `8100-8119` based on registry assignments.
```bash
# 1) Install/update registry-driven vllm launch script on Studio
./platform/ops/scripts/mlxctl mlx-launch-configure-vllm

# 2) Restart supervisor
./platform/ops/scripts/mlxctl mlx-launch-stop --ports 8100,8101,8102
./platform/ops/scripts/mlxctl mlx-launch-start

# 3) Validate runtime family + listeners
ssh studio "mlxctl status --checks"
ssh studio "lsof -nP -iTCP:8100-8102 -sTCP:LISTEN"
```

Quality gate (from repo host with Studio network access):
```bash
uv run python platform/ops/scripts/mlx_quality_gate.py --host 192.168.1.72 --json
```

## Studio SSH preflight + lock-state handling
Use this preflight before any long vLLM-metal run.

```bash
ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ControlMaster=no -o ControlPath=none studio "echo ssh-preflight-ok"
```

If preflight fails, classify by stderr text:
- `This system is locked...` -> `LOCKED` (host booted but needs local unlock/login).
- `Permission denied (publickey,...)` -> `AUTH_REJECTED` (key/auth path not accepted yet).
- `timed out` / `No route to host` -> `HOST_DOWN` (reboot/unreachable).
- `broken pipe` -> `TRANSPORT_ERROR` (session/socket instability; retry preflight and avoid multiplexing).

Operational defaults for automation:
- Use non-multiplexed SSH for `studio` (`ControlMaster=no`, `ControlPath=none`).
- Keep `BatchMode=yes` + `IdentitiesOnly=yes` on automation commands.
- Treat `LOCKED` as a hard stop until local unlock completes.

FileVault policy:
- `studio` currently runs with `FileVault: On`.
- After some reboots/crash cycles, local unlock may be required before remote automation is reliable.

## vLLM-metal experimental lane forensics (Studio)
When `metal-test-main` (`8121`) drops under load, run this probe to capture
request shape + process/listener state + logs in a single report.

```bash
source layer-gateway/litellm-orch/config/env.local

uv run python layer-inference/optillm-local/scripts/run_vllm_metal_failure_probe.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_failure_probe.example.json \
  --out /tmp/vllm_metal_failure_probe.json
```

Quick health checks:
```bash
curl -fsS http://127.0.0.1:4000/health | jq .
ssh studio "lsof -nP -iTCP -sTCP:LISTEN | egrep ':8120|:8121|:8122' || true"
ssh studio "ps -eo pid,ppid,etime,%cpu,%mem,rss,command | egrep 'vllm serve|8121' | grep -v egrep || true"
```

### Known `8121` crash class (async scheduler path)
If `metal-test-main` (`8121`) drops with LiteLLM error text:
`EngineCore encountered an issue`, check `/Users/thestudio/vllm-8121.log` first.

Confirmed failure signature:
- `AssertionError` in `vllm/v1/core/sched/async_scheduler.py`
- Followed by `EngineDeadError` and API server shutdown.

Mitigation (validated): run `8121` with async scheduling disabled and keep the
current tuned lane params (`mem_fraction=0.60`, `max_model_len=65536`).
```bash
ssh -o IdentitiesOnly=yes -o ControlMaster=no -o ControlPath=none studio \
  "pids=$(lsof -ti tcp:8121 -sTCP:LISTEN || true); \
   if [ -n \"$pids\" ]; then kill -9 $pids || true; fi; \
   nohup env VLLM_METAL_MEMORY_FRACTION=0.60 \
   /Users/thestudio/.venv-vllm-metal/bin/python3 \
   /Users/thestudio/.venv-vllm-metal/bin/vllm serve \
   /Users/thestudio/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4/snapshots/35386111fd494a54a4e3a3705758e280c44d9e9e \
   --served-model-name default_model --host 0.0.0.0 --port 8121 \
   --max-model-len 65536 --no-async-scheduling > /Users/thestudio/vllm-8121.log 2>&1 &"
```

Quick validation after mitigation:
```bash
# 1) Listener up
ssh studio "lsof -nP -iTCP:8121 -sTCP:LISTEN"

# 2) LiteLLM smoke
curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"metal-test-main","messages":[{"role":"user","content":"Reply with exactly: main-up"}],"max_tokens":16,"temperature":0.1}'

# 3) Repro gate (used to crash with async scheduler on)
uv run python - <<'PY'
import json, urllib.request, concurrent.futures
key = [l.split("=",1)[1].strip() for l in open("layer-gateway/litellm-orch/config/env.local") if l.startswith("LITELLM_MASTER_KEY=")][0]
payload = {
  "model":"metal-test-main",
  "messages":[
    {"role":"assistant","content":" ".join(["prior context"]*4500)},
    {"role":"user","content":"Summarize context."}
  ],
  "max_tokens":16384, "n":1, "temperature":0.2, "stream":False
}
def one():
  req = urllib.request.Request("http://127.0.0.1:4000/v1/chat/completions",
                               data=json.dumps(payload).encode(),
                               method="POST",
                               headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
  with urllib.request.urlopen(req, timeout=240) as r:
    return r.status
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  print([f.result() for f in [ex.submit(one), ex.submit(one)]])
PY
```

## vLLM-metal tuning (`max-model-len` x `VLLM_METAL_MEMORY_FRACTION`) on `8121`
Use this when you need a decision-grade shortlist for `metal-test-main` capacity
without changing routing contracts.

Phase A contract:
- direct lane traffic only (`http://192.168.1.72:8121`)
- fixed request shape for all candidates
- warmup requests discarded
- quiescence gate before each candidate
- startup early-reject signal from:
  - `GPU KV cache size: ... tokens`
  - `Maximum concurrency for ... tokens per request: ...x`

Run Phase A:
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_lane_tuning.example.json \
  --out /tmp/vllm_metal_lane_tuning_report_phaseA.json \
  --mode phaseA
```

Targeted main profile (current campaign default):
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_main_targeted_tuning.json \
  --out /tmp/vllm_metal_main_targeted_after_fix.json \
  --mode phaseA
```

Current `8121` canonical runtime (after contaminated-row recheck closure):
- `VLLM_METAL_MEMORY_FRACTION=0.60`
- `--max-model-len 65536`
- `--no-async-scheduling`
- Evidence:
  - `/tmp/vllm_metal_main_targeted_after_fix.json`
  - `/tmp/vllm_metal_main_contaminated_recheck.out.json`
  - `docs/journal/2026-02-27-vllm-metal-8121-main-contaminated-recheck-closure.md`

What the harness records per candidate (minimal set):
- pass/fail stability
- SSH preflight status + host-state classification (`LOCKED`, `AUTH_BLOCKED`, `UNREACHABLE`, `UNSTABLE`)
- startup KV cache tokens + max concurrency estimate
- peak running/waiting requests
- peak KV usage %
- client p50/p95 latency + tokens/sec
- engine version + non-default args

If a candidate fails with `host_state != READY`, treat it as environment-contaminated
and rerun only those candidates after preflight is stable.

Output artifacts:
- JSON: `/tmp/vllm_metal_lane_tuning_report_phaseA.json`
- Markdown scorecard: `/tmp/vllm_metal_lane_tuning_report_phaseA.md`

Post-run sanity (LiteLLM stays out of measurement loop, but verify gateway path):
```bash
source layer-gateway/litellm-orch/config/env.local
curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"metal-test-main","messages":[{"role":"user","content":"reply with: phaseA-ok"}],"max_tokens":16}' | jq .
```

## vLLM-metal targeted tuning on `8120` (`metal-test-fast`)
Use this focused profile to test only the likely winning direction for the fast
lane (larger `max-model-len` headroom with explicit memory fraction, async off).

Run targeted Phase A:
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_targeted_tuning.json \
  --out /tmp/vllm_metal_fast_targeted_report.json \
  --mode phaseA
```

Quick post-run health:
```bash
curl -fsS http://192.168.1.72:8120/health
curl -fsS http://192.168.1.72:8120/v1/models | jq .
ssh studio "uptime; last reboot | head -n 3"
```

## vLLM-metal targeted tuning on `8122` (`metal-test-deep`)
Use this profile to capture `metal-test-deep` overlap behavior with the same
fixed request shape used for `8120`/`8121`, and document cross-lane comparison.

Run targeted Phase A:
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_deep_targeted_tuning.json \
  --out /tmp/vllm_metal_deep_targeted_report.json \
  --mode phaseA
```

Restore non-paged baseline for `8122` after test:
```bash
ssh studio "pids=\$(lsof -ti tcp:8122 -sTCP:LISTEN || true); \
  if [ -n \"\$pids\" ]; then kill -9 \$pids || true; fi; \
  nohup env VLLM_METAL_MEMORY_FRACTION=0.60 \
  /Users/thestudio/.venv-vllm-metal/bin/python3 \
  /Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-120b-MXFP4-Q4/snapshots/bce781bef0f2fc85ed4e575af74054f5aad73ddd \
  --served-model-name default_model --host 0.0.0.0 --port 8122 \
  --max-model-len 65536 --no-async-scheduling > /Users/thestudio/vllm-8122.log 2>&1 &"
```

## vLLM-metal paged-attention workaround check on `8120`
Use this only for workaround validation when `8120` overlap crashes on the
default MLX-managed cache path.

Run paged Phase A profile:
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_paged_targeted_tuning.json \
  --out /tmp/vllm_metal_fast_paged.json \
  --mode phaseA
```

Current observed bounds:
- Paged startup can fail at high memory fractions with:
  `requested memory exceeds available RAM` (lower memory fraction, e.g. <= `0.48`).
- On current GPT-OSS fast lane stack, paged path also fails in warmup with:
  `AttributeError: 'AttentionBlock' object has no attribute 'n_heads'`
  from `vllm_metal/metal_kernel_backend/paged_attention.py`.

Restore non-paged baseline for `8120`:
```bash
ssh studio "pids=\$(lsof -ti tcp:8120 -sTCP:LISTEN || true); \
  if [ -n \"\$pids\" ]; then kill -9 \$pids || true; fi; \
  nohup env VLLM_METAL_MEMORY_FRACTION=0.60 \
  /Users/thestudio/.venv-vllm-metal/bin/python3 \
  /Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089 \
  --served-model-name default_model --host 0.0.0.0 --port 8120 \
  --max-model-len 32768 --no-async-scheduling > /Users/thestudio/vllm-8120.log 2>&1 &"
```
