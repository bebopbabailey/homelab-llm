# 2026-02-26 — vLLM-metal `8121` Phase A tuning harness implementation (blocked run)

## Goal
Implement the focused Phase A tuning workflow for `metal-test-main` (`8121`) with:
- direct-to-lane transport only,
- fixed request-shape contract,
- warmup + quiescence gates,
- startup early-reject (`KV cache size`, `Maximum concurrency`),
- minimal decision metrics.

## What was implemented

### New harness
- `layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py`
  - Candidate grid runner with mode flags (`phaseA|phaseB|all`).
  - Direct lane measurement path (`8121`) and no LiteLLM in-loop.
  - Warmup-discard + quiescence gate.
  - Startup signal parsing:
    - `GPU KV cache size: ... tokens`
    - `Maximum concurrency for ... tokens per request: ...x`
    - engine version + non-default args.
  - Minimal metrics collection:
    - pass/fail stability
    - peak running/waiting
    - peak KV usage %
    - client p50/p95 latency
    - client tokens/sec
  - Failure evidence capture (tail log + listeners + process snapshot).
  - JSON report + markdown scorecard output.
  - Added hard pre-launch cleanup for stale listeners:
    - kill by port listener (`lsof -ti tcp:<port> -sTCP:LISTEN`), then relaunch.

### New Phase A profile
- `layer-inference/optillm-local/config/viability_profiles/vllm_metal_lane_tuning.example.json`
  - Baseline reference: `262144/auto/async-off`.
  - Grid: `max_model_len=[32768,65536,131072]` x `memory_fraction=[auto,0.60,0.75]`.
  - Async off for Phase A.
  - Fixed request shape and fixed sweep (`1 -> 2 -> 4`).

### Runbook and task state
- Updated `layer-inference/RUNBOOK.md` with a dedicated tuning section.
- Updated `NOW.md` active work to this Phase A tuning task.

## Commands executed
```bash
python3 -m py_compile layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py

uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_lane_tuning.example.json \
  --out /tmp/vllm_metal_lane_tuning_report_phaseA.json \
  --mode phaseA
```

## Runtime blocker encountered
Phase A execution could not be completed because Studio became unavailable, then returned in a locked state:
- Host intermittently unreachable on `192.168.1.72`.
- Once reachable, SSH returned:
  - `This system is locked. To unlock it, use a local account name and password.`
  - `Permission denied (publickey,password,keyboard-interactive).`

Without unlocking Studio locally, candidate relaunch orchestration on `8121` cannot proceed.

## Current status
- Harness + profile + runbook updates are complete.
- Phase A run status: **UNVERIFIED (blocked by locked Studio host)**.

## Next step (once Studio is unlocked)
Run:
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_lane_tuning.example.json \
  --out /tmp/vllm_metal_lane_tuning_report_phaseA.json \
  --mode phaseA
```
Then review:
- `/tmp/vllm_metal_lane_tuning_report_phaseA.json`
- `/tmp/vllm_metal_lane_tuning_report_phaseA.md`
