# 2026-02-27 — vLLM-metal `8121` targeted Phase A after SSH hardening

## Summary
Executed targeted Phase A for `metal-test-main` (`8121`) using the hardened
harness (SSH preflight + host-state classification).

Follow-up closure entry:
`docs/journal/2026-02-27-vllm-metal-8121-main-contaminated-recheck-closure.md`.

Outcome was partially clean:
- 2 candidates passed with `host_state=READY`
- 4 candidates failed with `host_state=UNREACHABLE` / `ssh_error_class=HOST_DOWN`

This is a classified result, not ambiguous failure. The harness correctly
separated host instability from model-config behavior.

## Profile and artifacts
- Profile:
  `layer-inference/optillm-local/config/viability_profiles/vllm_metal_main_targeted_tuning.json`
- JSON report:
  `/tmp/vllm_metal_main_targeted_after_fix.json`
- Markdown scorecard:
  `/tmp/vllm_metal_main_targeted_after_fix.md`

## Clean candidate results (READY host state)
1. `a-ml32768-mem0.60-async-off`
- PASS
- startup max concurrency: `25.6x`
- startup KV tokens: `838848`
- `p95@c4`: `4.020395s`
- peak waiting: `0.0`
- peak KV usage: `0.004158...`

2. `a-ml32768-memauto-async-off`
- PASS
- startup max concurrency: `1.1x`
- startup KV tokens: `36032`
- early reject at c4 (as expected from low startup estimate)

Current winner from clean rows: `a-ml32768-mem0.60-async-off`.

## Contaminated candidates (rerun required)
- `a-ml65536-mem0.60-async-off`
- `a-ml65536-memauto-async-off`
- `a-ml131072-mem0.60-async-off`
- `a-ml131072-memauto-async-off`

Failure class on these rows: `UNREACHABLE/HOST_DOWN`.
Observed failure signatures include SSH banner timeout and temporary no-route
reachability issues while Studio became unreachable mid-campaign.

## Decision status
- Partial decision available now: `32768 + 0.60 + async off` is stable and strong.
- Final `8121` tuning closure is pending rerun of only contaminated rows once
  Studio preflight is stable.
- Closure completed in follow-up:
  `docs/journal/2026-02-27-vllm-metal-8121-main-contaminated-recheck-closure.md`.

## Next run command (contaminated rows only)
Build a temporary profile with only `max_model_len=[65536,131072]` and
`memory_fraction=["0.60","auto"]`, then run:

```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile /tmp/vllm_metal_main_contaminated_recheck.json \
  --out /tmp/vllm_metal_main_contaminated_recheck.out.json \
  --mode phaseA
```
