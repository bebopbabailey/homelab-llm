# 2026-02-26 — vLLM-metal `8120` targeted Phase A results (`metal-test-fast`)

Note: this entry reflects the pre-post117 window. See
`docs/journal/2026-02-27-gpt-oss-post117-reconciliation.md` for the reconciled
current interpretation.

## Goal
Create a reviewer-ready, fast-lane-specific record of the targeted Phase A sweep on
`metal-test-fast` (`8120`) and capture the exact failure signature.

## What was tested
- Harness: `layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py`
- Profile: `layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_targeted_tuning.json`
- Report artifacts:
  - `/tmp/vllm_metal_fast_targeted_report.json`
  - `/tmp/vllm_metal_fast_targeted_report.md`
- Runtime path: direct to Studio lane `http://192.168.1.72:8120` (LiteLLM excluded for Phase A measurement)

## Fixed request shape (held constant)
- `n=1`
- `history_chars=4000`
- `max_tokens=256`
- warmup: 2 requests at `concurrency=1`
- measured sweep: `concurrency=[1,2,4]`, `requests_per_stage=6`
- async scheduling: OFF for all Phase A candidates

## Candidate matrix and outcomes

| candidate | `max_model_len` | `VLLM_METAL_MEMORY_FRACTION` | startup KV cache tokens | startup max concurrency line | result |
| --- | ---: | --- | ---: | ---: | --- |
| `ref-ml65536-memauto-async-off` | 65536 | `auto` | 72,080 | 1.1x | FAIL at `c2` (early-reject hit, but `c2` still failed) |
| `a-ml32768-mem0.60-async-off` | 32768 | `0.60` | 1,677,712 | 51.2x | FAIL at `c2` |
| `a-ml65536-mem0.60-async-off` | 65536 | `0.60` | 1,677,712 | 25.6x | FAIL at `c2` |
| `a-ml131072-mem0.60-async-off` | 131072 | `0.60` | 1,677,712 | 12.8x | FAIL at `c2` |

## Failure signature (repeated across candidates)
- API failure at overlap stage: `500 EngineCore encountered an issue`
- Engine crash trace in `/Users/thestudio/vllm-8120.log` includes:
  - `_merge_kv_caches` in `vllm_metal/v1/model_runner.py`
  - `BatchKVCache.merge` in `mlx_lm/models/cache.py`
  - `ValueError: [broadcast_shapes] Shapes (1,8,662,64) and (1,8,128,64) cannot be broadcast`

## Interpretation
- This run did **not** find a stable overlap envelope for `metal-test-fast` under the
  tested shape; all configs failed when moving from single-flight to overlap (`c2`).
- The failure pattern is consistent with a KV-cache merge shape mismatch path under
  concurrent decode, not simple unified-memory exhaustion:
  - the same run shows very high startup headroom for `mem_fraction=0.60`
  - failure remains at `c2` across all tested `max_model_len` values

## Current lane state at close
- `8120` up and healthy after relaunch.
- `GET /v1/models` on `8120` returns `default_model`.
- listener check showed `8120` and `8121` active.

## Evidence commands
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_fast_targeted_tuning.json \
  --out /tmp/vllm_metal_fast_targeted_report.json \
  --mode phaseA

curl -fsS http://192.168.1.72:8120/health
curl -fsS http://192.168.1.72:8120/v1/models | jq .
ssh studio "lsof -nP -iTCP -sTCP:LISTEN | egrep ':8120|:8121|:8122|:4020' || true"
```

## Outcome
- Status: PASS (documentation and evidence codification complete)
- Decision support: keep `metal-test-fast` overlap-constrained (`concurrency=1`)
  for now; treat this as backend bug-path behavior pending upstream fix.
