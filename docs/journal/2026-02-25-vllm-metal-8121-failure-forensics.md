# 2026-02-25 — vLLM-metal `8121` failure forensics (`metal-test-main`)

## Goal
Reproduce and explain why `metal-test-main` on Studio port `8121` intermittently
fails under OpenWebUI/LiteLLM load, then restore lane health and define a safe
near-term request envelope.

## What was tested
- Tool: `layer-inference/optillm-local/scripts/run_vllm_metal_failure_probe.py`
- Baseline profile: `layer-inference/optillm-local/config/viability_profiles/vllm_metal_failure_probe.example.json`
- Stress profile (temporary): `/tmp/vllm_metal_failure_probe_stress.json`
- Routing path: `OWUI/LiteLLM -> metal-test-main -> Studio 8121 (vllm-metal)`

## Results
### 1) Baseline profile: PASS
- Report: `/tmp/vllm_metal_failure_probe_baseline_20260225_093526.json`
- Scenarios passed:
  - `n=1, max_tokens=64, concurrency=2` (4/4 success, p50 ~0.891s)
  - `n=2, max_tokens=256, concurrency=2` (4/4 success, p50 ~1.543s)
  - `n=4, max_tokens=1886, concurrency=1, history_chars=14000` (1/1 success, ~4.984s)

### 2) Stress profile: FAIL (reproduced)
- Report: `/tmp/vllm_metal_failure_probe_stress_20260225_093548.json`
- Failing scenario:
  - `n=4, max_tokens=1886, concurrency=2, repeats=2, history_chars=24000`
- Outcome:
  - 0/2 success in first repeat
  - LiteLLM surfaced `500 EngineCore encountered an issue`
  - Studio listeners after failure: `8120=true`, `8121=false`, `8122=true`
- Forensic evidence:
  - `runningboardd ... termination reported by proc_exit`
  - `launchd ... signaled service: Killed: 9`
  - `launchd ... service state: SIGKILLed`

## Interpretation
- The failure is load-shape dependent, not a request-schema mismatch.
- `8121` tolerates high `n/max_tokens` when single-flight, but drops when the
  same heavy shape is made concurrent (`concurrency=2`) with very large context.
- Practical current boundary for `metal-test-main`:
  - **Safer**: heavy single-flight (`concurrency=1`) even with `n=4`.
  - **Risky**: heavy multi-flight (`concurrency>=2`) at large context + large outputs.

## Recovery performed
- Relaunched only Studio lane `8121` with the same vllm-metal command used by
  the lane.
- Verified listeners restored on `8120/8121/8122`.
- Verified `/v1/models` responds on `8121`.

## Evidence commands
```bash
set -a && source layer-gateway/litellm-orch/config/env.local && set +a

uv run python layer-inference/optillm-local/scripts/run_vllm_metal_failure_probe.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_failure_probe.example.json \
  --out /tmp/vllm_metal_failure_probe_baseline_20260225_093526.json

uv run python layer-inference/optillm-local/scripts/run_vllm_metal_failure_probe.py \
  --profile /tmp/vllm_metal_failure_probe_stress.json \
  --out /tmp/vllm_metal_failure_probe_stress_20260225_093548.json

ssh studio "lsof -nP -iTCP -sTCP:LISTEN | egrep ':8120|:8121|:8122' || true"
ssh studio "ps -eo pid,ppid,etime,%cpu,%mem,rss,command | egrep 'vllm serve|8120|8121|8122' | grep -v egrep || true"
```

## Outcome
- Status: PASS (FAST forensics + recovery)
- Decision support: vllm-metal is viable for this lane, but needs guarded heavy
  request envelopes before BoN-style parallel candidate work.
