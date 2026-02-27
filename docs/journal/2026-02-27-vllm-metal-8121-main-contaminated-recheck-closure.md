# 2026-02-27 — vLLM-metal `8121` contaminated-row recheck closure (`metal-test-main`)

## Summary
Resumed the blocked `8121` campaign and reran only the previously
environment-contaminated rows (`65536/131072` x `0.60/auto`, async off).

Result:
- Recheck run completed with `4/4 PASS`
- `host_state=READY` for all candidates
- no SSH classification failures during this rerun

This closes the prior `HOST_DOWN/UNREACHABLE` contamination from:
`/tmp/vllm_metal_main_targeted_after_fix.json`.

## Commands and artifacts
Run command:

```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile /tmp/vllm_metal_main_contaminated_recheck.json \
  --out /tmp/vllm_metal_main_contaminated_recheck.out.json \
  --mode phaseA
```

Artifacts:
- prior targeted run: `/tmp/vllm_metal_main_targeted_after_fix.json`
- contaminated-row recheck: `/tmp/vllm_metal_main_contaminated_recheck.out.json`
- recheck scorecard: `/tmp/vllm_metal_main_contaminated_recheck.out.md`

## Combined clean ranking (READY + PASS rows)
Across both artifacts, combined clean ranking was:

1. `a-ml65536-mem0.60-async-off`
   - `p95@c4`: `4.01872s`
   - startup max concurrency: `12.8x`
   - startup KV tokens: `838,848`
2. `a-ml32768-mem0.60-async-off`
   - `p95@c4`: `4.020395s`
   - startup max concurrency: `25.6x`
   - startup KV tokens: `838,848`
3. `a-ml131072-mem0.60-async-off`
   - `p95@c4`: `4.045305s`
   - startup max concurrency: `6.4x`
   - startup KV tokens: `838,848`

`memory_fraction=auto` candidates remained early-reject (`~1.1x` startup
concurrency estimate) and did not enter full `c4` measurement.

## Decision
Canonical `metal-test-main` (`8121`) runtime for now:
- `VLLM_METAL_MEMORY_FRACTION=0.60`
- `--max-model-len 65536`
- `--no-async-scheduling`

Rationale:
- best `p95@c4` in clean combined rows
- materially more context headroom than `32768`
- stable under fixed-shape overlap test contract

## Notes
- This closes the `8121` targeted Phase A tuning loop from an operational
  standpoint.
- No routing contract/model alias changes were made in this step.
