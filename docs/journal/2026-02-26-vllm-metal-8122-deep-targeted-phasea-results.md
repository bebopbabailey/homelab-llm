# 2026-02-26 — vLLM-metal `8122` targeted Phase A results (`metal-test-deep`)

Note: this entry reflects the pre-post117 window. See
`docs/journal/2026-02-27-gpt-oss-post117-reconciliation.md` for the reconciled
current interpretation.

## Goal
Run the same focused Phase A harness contract on `metal-test-deep` (`8122`) to
confirm whether overlap concurrency is currently viable, and document lane-level
comparison against `metal-test-fast` (`8120`).

## What was tested
- Harness: `layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py`
- Profile: `layer-inference/optillm-local/config/viability_profiles/vllm_metal_deep_targeted_tuning.json`
- Artifacts:
  - `/tmp/vllm_metal_deep_targeted_report.json`
  - `/tmp/vllm_metal_deep_targeted_report.md`
- Runtime path: direct lane calls to `http://192.168.1.72:8122` (LiteLLM excluded from measurement loop)

## Fixed request shape
- `n=1`
- `history_chars=4000`
- `max_tokens=256`
- warmup: 2 requests at `concurrency=1`
- measured sweep: `concurrency=[1,2,4]`, `requests_per_stage=6`
- async scheduling: OFF for all candidates

## Candidate outcomes

| candidate | `max_model_len` | `VLLM_METAL_MEMORY_FRACTION` | startup KV cache tokens | startup max concurrency line | result |
| --- | ---: | --- | ---: | ---: | --- |
| `ref-ml131072-memauto-async-off` | 131072 | `auto` | 144,176 | 1.1x | FAIL at `c2` |
| `a-ml32768-memauto-async-off` | 32768 | `auto` | 36,032 | 1.1x | FAIL at `c2` |
| `a-ml32768-mem0.60-async-off` | 32768 | `0.60` | 1,118,480 | 34.13x | FAIL at `c2` |
| `a-ml65536-memauto-async-off` | 65536 | `auto` | 72,080 | 1.1x | FAIL at `c2` |
| `a-ml65536-mem0.60-async-off` | 65536 | `0.60` | 1,118,480 | 17.07x | FAIL at `c2` |

## Failure signature
The deep lane reproduced the same fatal overlap crash class observed on fast:
- API surface: `500 EngineCore encountered an issue`
- Engine trace in `/Users/thestudio/vllm-8122.log` includes:
  - `vllm_metal/v1/model_runner.py::_merge_kv_caches`
  - `mlx_lm/models/cache.py::BatchKVCache.merge`
  - `ValueError: [broadcast_shapes] Shapes (1,8,662,64) and (1,8,128,64) cannot be broadcast`

## Interpretation
- `metal-test-deep` is currently overlap-constrained in the same way as
  `metal-test-fast`: all tested configs passed single-flight and failed at `c2`.
- Increasing startup headroom (`mem_fraction=0.60`, high estimated max
  concurrency) did not remove the crash class, which supports a backend merge
  bug path rather than a simple capacity-only limit.

## Lane state after run
`8122` was restored to non-paged baseline and validated healthy:
- `VLLM_METAL_MEMORY_FRACTION=0.60`
- `--max-model-len 65536`
- `--no-async-scheduling`
- `/health` returns 200 and `/v1/models` returns `default_model`.

## Evidence commands
```bash
uv run python layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py \
  --profile layer-inference/optillm-local/config/viability_profiles/vllm_metal_deep_targeted_tuning.json \
  --out /tmp/vllm_metal_deep_targeted_report.json \
  --mode phaseA

ssh studio "tail -n 220 /Users/thestudio/vllm-8122.log"
curl -fsS http://192.168.1.72:8122/health
curl -fsS http://192.168.1.72:8122/v1/models | jq .
```

## Outcome
- Status: PASS (targeted deep run + documentation complete)
- Decision support: treat GPT-OSS vLLM-metal experimental lanes as
  `concurrency=1` effective posture until upstream fix lands for this crash class.
